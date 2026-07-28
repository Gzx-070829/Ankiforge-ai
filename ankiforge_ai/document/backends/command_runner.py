from __future__ import annotations

import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from typing import Optional

from ..errors import DocumentImportError
from ..serialization import document_from_safe_json
from .base import BackendCommand, BackendResult
from .output_validation import validate_safe_output_text


DEFAULT_BACKEND_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_STDOUT_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_STDERR_BYTES = 64 * 1024
_MAX_ARGUMENTS = 32
_MAX_ARGUMENT_CHARS = 2_048
_MAX_TOTAL_ARGUMENT_CHARS = 8_192
_WINDOWS_CREATE_SUSPENDED = 0x00000004
_URI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
_FORBIDDEN_SWITCHES = (
    "--bibliography",
    "--data-dir",
    "--extract-media",
    "--filter",
    "--include",
    "--lua-filter",
    "--metadata-file",
    "--pdf-engine",
    "--request-header",
    "--resource-path",
    "--template",
)


def _error(code: str, action: str = "check_backend") -> DocumentImportError:
    return DocumentImportError(
        code=code,
        message_key=f"document.error.{code}",
        action_key=f"document.action.{action}",
    )


class _WindowsJobObject:
    _KILL_ON_JOB_CLOSE = 0x00002000
    _EXTENDED_LIMIT_INFORMATION = 9
    _WAIT_OBJECT_0 = 0
    _WAIT_MILLISECONDS = 5_000

    def __init__(self, handle, kernel32) -> None:
        self._handle = handle
        self._kernel32 = kernel32
        self._closed = False

    @classmethod
    def assign(cls, process):
        if os.name != "nt":
            raise OSError("Windows Job Objects are unavailable")
        import ctypes
        from ctypes import wintypes

        class BasicLimitInformation(ctypes.Structure):
            _fields_ = (
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            )

        class IoCounters(ctypes.Structure):
            _fields_ = (
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            )

        class ExtendedLimitInformation(ctypes.Structure):
            _fields_ = (
                ("BasicLimitInformation", BasicLimitInformation),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            )

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        )
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = (
            wintypes.HANDLE,
            wintypes.HANDLE,
        )
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
        kernel32.TerminateJobObject.restype = wintypes.BOOL
        kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise OSError("job creation failed")
        job = cls(handle, kernel32)
        try:
            information = ExtendedLimitInformation()
            information.BasicLimitInformation.LimitFlags = cls._KILL_ON_JOB_CLOSE
            if not kernel32.SetInformationJobObject(
                handle,
                cls._EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(information),
                ctypes.sizeof(information),
            ):
                raise OSError("job limit setup failed")
            process_handle = wintypes.HANDLE(int(process._handle))
            if not kernel32.AssignProcessToJobObject(handle, process_handle):
                raise OSError("job assignment failed")
        except (AttributeError, OSError, TypeError, ValueError):
            job._close()
            raise OSError("job containment failed") from None
        return job

    def terminate_and_wait(self) -> None:
        if self._closed:
            return
        failed = False
        try:
            if not self._kernel32.TerminateJobObject(self._handle, 1):
                failed = True
            elif (
                self._kernel32.WaitForSingleObject(
                    self._handle,
                    self._WAIT_MILLISECONDS,
                )
                != self._WAIT_OBJECT_0
            ):
                failed = True
        finally:
            if not self._close():
                failed = True
        if failed:
            raise OSError("job cleanup failed")

    def _close(self) -> bool:
        if self._closed:
            return True
        closed = bool(self._kernel32.CloseHandle(self._handle))
        self._closed = True
        return closed


class SafeCommandRunner:
    def __init__(
        self,
        *,
        timeout_seconds: float = DEFAULT_BACKEND_TIMEOUT_SECONDS,
        max_stdout_bytes: int = DEFAULT_MAX_STDOUT_BYTES,
        max_stderr_bytes: int = DEFAULT_MAX_STDERR_BYTES,
        temp_parent: Optional[Path] = None,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not 0 < timeout_seconds <= 300
        ):
            raise ValueError("timeout_seconds must be in (0, 300]")
        for name, value, maximum in (
            ("max_stdout_bytes", max_stdout_bytes, DEFAULT_MAX_STDOUT_BYTES),
            ("max_stderr_bytes", max_stderr_bytes, DEFAULT_MAX_STDERR_BYTES),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 < value <= maximum
            ):
                raise ValueError(f"{name} must be positive and bounded")
        if temp_parent is not None:
            parent = Path(temp_parent)
            try:
                if (
                    not parent.is_absolute()
                    or not parent.is_dir()
                    or parent.is_symlink()
                ):
                    raise OSError
                parent = parent.resolve(strict=True)
            except OSError:
                raise ValueError("temp_parent must be a controlled directory") from None
        else:
            parent = None
        self._timeout_seconds = float(timeout_seconds)
        self._max_stdout_bytes = max_stdout_bytes
        self._max_stderr_bytes = max_stderr_bytes
        self._temp_parent = parent

    def run(self, command: BackendCommand, *, cancellation=None) -> BackendResult:
        executable, arguments, source = self._validate_command(command)
        if _is_cancelled(cancellation):
            raise _error("backend_cancelled", "retry_import")

        with _controlled_temporary_directory(
            prefix="ankiforge-document-",
            dir=str(self._temp_parent) if self._temp_parent is not None else None,
        ) as temporary:
            working_directory = Path(temporary).resolve(strict=True)
            environment = _sanitized_environment(working_directory)
            argv = [str(executable), *arguments, str(source)]
            if os.name == "nt":
                try:
                    process = _start_windows_suspended_process(
                        argv,
                        working_directory,
                        environment,
                    )
                except (OSError, ValueError):
                    raise _error("backend_unavailable", "enable_backend") from None
                containment = None
                try:
                    containment = _WindowsJobObject.assign(process)
                    _resume_suspended_windows_process(process)
                except OSError:
                    _cleanup_windows_start_failure(process, containment)
                    raise _error(
                        "backend_containment_failed",
                        "enable_backend",
                    ) from None
            else:
                containment = None
                try:
                    process = subprocess.Popen(
                        argv,
                        shell=False,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=str(working_directory),
                        env=environment,
                        creationflags=0,
                        start_new_session=True,
                        close_fds=True,
                    )
                except (OSError, ValueError):
                    raise _error("backend_unavailable", "enable_backend") from None

            stdout = bytearray()
            stderr = bytearray()
            stdout_overflow = threading.Event()
            stderr_overflow = threading.Event()
            stdout_thread = threading.Thread(
                target=_drain_pipe,
                args=(
                    process.stdout,
                    stdout,
                    self._max_stdout_bytes,
                    stdout_overflow,
                ),
                daemon=True,
                name="ankiforge-backend-stdout",
            )
            stderr_thread = threading.Thread(
                target=_drain_pipe,
                args=(
                    process.stderr,
                    stderr,
                    self._max_stderr_bytes,
                    stderr_overflow,
                ),
                daemon=True,
                name="ankiforge-backend-stderr",
            )
            stdout_thread.start()
            stderr_thread.start()
            started = time.monotonic()
            failure_code = None
            containment_failure = False
            try:
                while process.poll() is None:
                    if _is_cancelled(cancellation):
                        failure_code = "backend_cancelled"
                        break
                    if stdout_overflow.is_set() or stderr_overflow.is_set():
                        failure_code = "backend_output_too_large"
                        break
                    if time.monotonic() - started >= self._timeout_seconds:
                        failure_code = "backend_timeout"
                        break
                    time.sleep(0.01)
                if failure_code is not None:
                    if containment is not None:
                        try:
                            containment.terminate_and_wait()
                        except OSError:
                            containment_failure = True
                    else:
                        _terminate_process_tree(process)
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    _kill_process_tree(process)
                    try:
                        process.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                if containment is not None:
                    try:
                        containment.terminate_and_wait()
                    except OSError:
                        containment_failure = True
                elif process.poll() is None:
                    _kill_process_tree(process)
                    try:
                        process.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        pass
                stdout_thread.join(timeout=2.0)
                stderr_thread.join(timeout=2.0)
                _close_process_streams(process)

            if containment_failure:
                raise _error("backend_containment_failed", "retry_import")
            if (
                failure_code is None
                and (stdout_overflow.is_set() or stderr_overflow.is_set())
            ):
                failure_code = "backend_output_too_large"
            if failure_code is not None:
                action = (
                    "retry_import"
                    if failure_code in {"backend_cancelled", "backend_timeout"}
                    else "check_backend"
                )
                raise _error(failure_code, action)
            if process.returncode != 0:
                raise _error("backend_failed")

            if command.output_artifact_suffix is not None:
                output = _read_output_artifact(
                    working_directory,
                    command.output_artifact_suffix,
                    self._max_stdout_bytes,
                    command.output_format,
                )
            else:
                output = _decode_and_validate_output(
                    bytes(stdout),
                    command.output_format,
                )
            stderr_summary = "backend_stderr_present" if stderr else ""
            return BackendResult(
                returncode=process.returncode,
                stdout=output,
                stderr_summary=stderr_summary,
            )

    @staticmethod
    def _validate_command(command: BackendCommand):
        if not isinstance(command, BackendCommand):
            raise _error("invalid_backend_command")
        executable_raw = command.executable
        if not isinstance(executable_raw, (str, Path)):
            raise _error("invalid_backend_command")
        executable_text = str(executable_raw)
        if (
            not executable_text
            or "\x00" in executable_text
            or _URI.match(executable_text)
        ):
            raise _error("invalid_backend_command")
        executable = Path(executable_text)
        try:
            if not executable.is_absolute():
                raise OSError
            executable = executable.resolve(strict=True)
            if not executable.is_file():
                raise OSError
        except OSError:
            raise _error("invalid_backend_command") from None

        source_raw = command.source_path
        if not isinstance(source_raw, (str, Path)):
            raise _error("invalid_local_file")
        source_text = str(source_raw)
        if not source_text or "\x00" in source_text or _URI.match(source_text):
            raise _error("invalid_local_file")
        source = Path(source_text)
        try:
            if not source.is_absolute() or source.is_symlink():
                raise OSError
            source = source.resolve(strict=True)
            if not source.is_file():
                raise OSError
        except OSError:
            raise _error("invalid_local_file", "reselect_file") from None

        if not isinstance(command.arguments, tuple):
            raise _error("invalid_backend_command")
        if len(command.arguments) > _MAX_ARGUMENTS:
            raise _error("invalid_backend_command")
        arguments = []
        total_chars = 0
        for argument in command.arguments:
            if (
                not isinstance(argument, str)
                or not argument
                or len(argument) > _MAX_ARGUMENT_CHARS
                or "\x00" in argument
                or "\r" in argument
                or "\n" in argument
                or _URI.match(argument)
            ):
                raise _error("invalid_backend_command")
            lowered = argument.casefold()
            if any(
                lowered == switch or lowered.startswith(f"{switch}=")
                for switch in _FORBIDDEN_SWITCHES
            ):
                raise _error("invalid_backend_command")
            total_chars += len(argument)
            if total_chars > _MAX_TOTAL_ARGUMENT_CHARS:
                raise _error("invalid_backend_command")
            arguments.append(argument)
        if command.output_format not in {"text", "json", "document_ir_json"}:
            raise _error("invalid_backend_command")
        if command.output_artifact_suffix not in {None, ".md"}:
            raise _error("invalid_backend_command")
        return executable, tuple(arguments), source


def _start_windows_suspended_process(argv, working_directory, environment):
    # CREATE_SUSPENDED guarantees the validated target cannot execute before
    # assignment to the kill-on-close Job Object and an explicit thread resume.
    return subprocess.Popen(
        argv,
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(working_directory),
        env=environment,
        creationflags=(
            _WINDOWS_CREATE_SUSPENDED
            | subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW
        ),
        close_fds=True,
    )


def _resume_suspended_windows_process(process) -> None:
    if os.name != "nt":
        raise OSError("Windows thread APIs are unavailable")
    import ctypes
    from ctypes import wintypes

    class ThreadEntry32(ctypes.Structure):
        _fields_ = (
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD),
            ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", wintypes.LONG),
            ("tpDeltaPri", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
        )

    thread_snapshot_flag = 0x00000004
    thread_suspend_resume_access = 0x0002
    resume_failed = 0xFFFFFFFF
    error_no_more_files = 18
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Thread32First.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ThreadEntry32),
    )
    kernel32.Thread32First.restype = wintypes.BOOL
    kernel32.Thread32Next.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ThreadEntry32),
    )
    kernel32.Thread32Next.restype = wintypes.BOOL
    kernel32.OpenThread.argtypes = (
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    )
    kernel32.OpenThread.restype = wintypes.HANDLE
    kernel32.ResumeThread.argtypes = (wintypes.HANDLE,)
    kernel32.ResumeThread.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL

    snapshot = kernel32.CreateToolhelp32Snapshot(thread_snapshot_flag, 0)
    if snapshot == wintypes.HANDLE(-1).value:
        raise OSError("thread snapshot failed")
    thread_ids = []
    snapshot_close_failed = False
    try:
        entry = ThreadEntry32()
        entry.dwSize = ctypes.sizeof(entry)
        if not kernel32.Thread32First(snapshot, ctypes.byref(entry)):
            raise OSError("thread enumeration failed")
        while True:
            if int(entry.th32OwnerProcessID) == int(process.pid):
                thread_ids.append(int(entry.th32ThreadID))
            entry.dwSize = ctypes.sizeof(entry)
            if kernel32.Thread32Next(snapshot, ctypes.byref(entry)):
                continue
            if ctypes.get_last_error() != error_no_more_files:
                raise OSError("thread enumeration failed")
            break
    finally:
        snapshot_close_failed = not bool(kernel32.CloseHandle(snapshot))
    if snapshot_close_failed or len(thread_ids) != 1:
        raise OSError("suspended thread unavailable")

    thread = kernel32.OpenThread(
        thread_suspend_resume_access,
        False,
        thread_ids[0],
    )
    if not thread:
        raise OSError("thread open failed")
    close_failed = False
    try:
        previous_suspend_count = kernel32.ResumeThread(thread)
        if previous_suspend_count != 1 and previous_suspend_count != resume_failed:
            raise OSError("unexpected suspend count")
        if previous_suspend_count == resume_failed:
            raise OSError("thread resume failed")
    finally:
        close_failed = not bool(kernel32.CloseHandle(thread))
    if close_failed:
        raise OSError("thread close failed")


def _cleanup_windows_start_failure(process, containment) -> None:
    if containment is not None:
        try:
            containment.terminate_and_wait()
        except OSError:
            pass
    else:
        try:
            process.kill()
        except OSError:
            pass
    _await_process(process)
    _close_process_streams(process)


def _await_process(process) -> None:
    try:
        process.wait(timeout=2.0)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _close_process_streams(process) -> None:
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass


@contextmanager
def _controlled_temporary_directory(*, prefix: str, dir: Optional[str]):
    try:
        temporary = tempfile.TemporaryDirectory(prefix=prefix, dir=dir)
    except OSError:
        raise _error("backend_cleanup_failed", "retry_import") from None
    try:
        yield temporary.name
    finally:
        try:
            temporary.cleanup()
        except OSError:
            raise _error("backend_cleanup_failed", "retry_import") from None


def _sanitized_environment(working_directory: Path):
    temporary = str(working_directory)
    environment = {
        "HOME": temporary,
        "TEMP": temporary,
        "TMP": temporary,
        "TMPDIR": temporary,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "DOCLING_OCR_ENABLED": "0",
        "MARKITDOWN_ENABLE_PLUGINS": "0",
    }
    if os.name == "nt":
        for name in ("SYSTEMROOT", "WINDIR"):
            value = os.environ.get(name)
            if value:
                environment[name] = value
    else:
        environment["LC_ALL"] = "C.UTF-8"
    return environment


def _drain_pipe(stream, destination, limit, overflow):
    if stream is None:
        return
    try:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                return
            remaining = limit - len(destination)
            if remaining > 0:
                destination.extend(chunk[:remaining])
            if len(chunk) > remaining:
                overflow.set()
                return
    except (OSError, ValueError):
        return


def _is_cancelled(cancellation) -> bool:
    if cancellation is None:
        return False
    method = getattr(cancellation, "is_set", None)
    if not callable(method):
        raise TypeError("cancellation must expose is_set()")
    return bool(method())


def _terminate_process_tree(process) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError, ValueError):
        try:
            process.terminate()
        except OSError:
            pass
    deadline = time.monotonic() + 0.5
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    if process.poll() is None:
        _kill_process_tree(process)


def _kill_process_tree(process) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError, ValueError):
        try:
            process.kill()
        except OSError:
            pass


def _decode_and_validate_output(payload: bytes, output_format: str) -> str:
    try:
        output = payload.decode("utf-8")
    except UnicodeDecodeError:
        raise _error("backend_invalid_output") from None
    try:
        validate_safe_output_text(output)
    except ValueError:
        raise _error("backend_invalid_output")
    if output_format in {"json", "document_ir_json"}:
        try:
            json.loads(
                output,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_non_finite,
            )
        except (json.JSONDecodeError, RecursionError, UnicodeError, ValueError):
            raise _error("backend_invalid_output") from None
    if output_format == "document_ir_json":
        try:
            document_from_safe_json(output)
        except (TypeError, ValueError):
            raise _error("backend_invalid_output") from None
    return output


def _read_output_artifact(
    working_directory: Path,
    suffix: str,
    max_bytes: int,
    output_format: str,
) -> str:
    try:
        root_candidates = []
        nested_candidate = False
        for current, directories, files in os.walk(
            working_directory,
            topdown=True,
            followlinks=False,
        ):
            current_path = Path(current)
            entries = tuple(directories) + tuple(files)
            for name in entries:
                if not name.casefold().endswith(suffix):
                    continue
                candidate = current_path / name
                if current_path != working_directory:
                    nested_candidate = True
                    continue
                root_candidates.append(candidate)
        if nested_candidate or len(root_candidates) != 1:
            raise OSError
        artifact = root_candidates[0]
        if artifact.is_symlink() or not artifact.is_file():
            raise OSError
        with artifact.open("rb") as handle:
            payload = handle.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise OSError
    except OSError:
        raise _error("backend_invalid_output") from None
    return _decode_and_validate_output(payload, output_format)


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_non_finite(value):
    raise ValueError("non-finite JSON number")
