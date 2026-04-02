"""
Custom exception classes for PrivateGPT.
"""


class PrivateGPTError(Exception):
    """Base exception for PrivateGPT."""
    pass


class AuthenticationError(PrivateGPTError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(PrivateGPTError):
    """Raised when user lacks permissions."""
    pass


class DocumentNotFoundError(PrivateGPTError):
    """Raised when a document is not found."""
    pass


class DocumentProcessingError(PrivateGPTError):
    """Raised when document ingestion fails."""
    pass


class ModelNotLoadedError(PrivateGPTError):
    """Raised when LLM model is not loaded."""
    pass


class VectorStoreError(PrivateGPTError):
    """Raised when FAISS operations fail."""
    pass


class TenantIsolationError(PrivateGPTError):
    """Raised on cross-tenant access attempt."""
    pass
