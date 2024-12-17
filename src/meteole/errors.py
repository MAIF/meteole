import xmltodict


class GenericMeteofranceApiError(Exception):
    """Exception raised errors in the input parameters where a required field is missing.

    Parameters
        ----------
        message : str
            Human-readable string descipting the exceptetion.
        description : str
            More detailed description of the error."""

    def init(self, text: str):
        """Initialize the exception with an error message parsed from an XML
        string.

        Parameters
        ----------
        text str:
            XML string containing the error details,
            expected to follow a specific schema with 'am:fault' as the root
            element and 'am:message' and 'am:description' as child elements."""

        # parse the error message with xmltodict
        data = xmltodict.parse(text)
        message = data["am:fault"]["am:message"]
        description = data["am:fault"]["am:description"]
        self.message = f"{message}\n {description}"
        super().__init__(self.message)


class MissingDataError(Exception):
    """Exception raised errors in the input data is missing"""

    def init(self, text: str):
        """Initialize the exception with an error message parsed from an XML
        string.

        Parameters
        ----------
        text str:
            XML string containing the error details,
            expected to follow a specific schema with 'am:fault' as the root
            element and 'am:message' and 'am:description' as child elements."""

        # parse the error message with xmltodict
        try:
            data = xmltodict.parse(text)
            exception = data["mw:fault"]["mw:description"]["ns0:ExceptionReport"]["ns0:Exception"]
            code = exception["@exceptionCode"]
            locator = exception["@locator"]
            text = exception["ns0:ExceptionText"]
            message = f"Error code: {code}\nLocator: {locator}\nText: {text}"
        except Exception:
            message = text
        self.message = message
        super().__init__(self.message)
