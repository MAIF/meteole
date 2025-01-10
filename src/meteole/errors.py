"""Error implementations"""

from __future__ import annotations

from typing import Any, MutableMapping

import xmltodict


class GenericMeteofranceApiError(Exception):
    """Exception raised when a required field is missing in the input parameters.

    Args:
        message: Human-readable string describing the exception.
        description: More detailed description of the error.
    """

    def __init__(self, text: str) -> None:
        """Initialize the exception with an error message parsed from an XML
        string.

        Args:
            text: XML string containing the error details,
                expected to follow a specific schema with 'am:fault' as the root
                element and 'am:message' and 'am:description' as child elements."""
        try:
            # Parse error message with xmltodict
            data: MutableMapping[str, Any] = xmltodict.parse(text)
            msg_content: str = data["am:fault"]["am:message"]
            description: str = data["am:fault"]["am:description"]
            message: str = f"{msg_content}\n {description}"
        except Exception:
            message = text

        super().__init__(message)


class MissingDataError(Exception):
    """Exception raised errors in the input data is missing"""

    def __init__(self, text: str) -> None:
        """Initialize the exception with an error message parsed from an XML
        string.

        Args:
            text: XML string containing the error details,
                expected to follow a specific schema with 'am:fault' as the root
                element and 'am:message' and 'am:description' as child elements."""

        try:
            # Parse error message with xmltodict
            data: MutableMapping[str, Any] = xmltodict.parse(text)
            exception: dict[Any, Any] = data["mw:fault"]["mw:description"]["ns0:ExceptionReport"]["ns0:Exception"]
            code: str = exception["@exceptionCode"]
            locator: str = exception["@locator"]
            exception_text: str = exception["ns0:ExceptionText"]
            message: str = f"Error code: {code}\nLocator: {locator}\nText: {exception_text}"
        except Exception:
            message = text

        super().__init__(message)
