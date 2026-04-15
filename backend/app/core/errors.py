from __future__ import annotations


class IMCError(Exception):
    """Base error for the application."""

    code: str = "imc_error"
    status: int = 400

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ParseError(IMCError):
    code = "parse_error"
    status = 422


class SessionNotFound(IMCError):
    code = "session_not_found"
    status = 404


class UnsupportedFileError(IMCError):
    code = "unsupported_file"
    status = 415
