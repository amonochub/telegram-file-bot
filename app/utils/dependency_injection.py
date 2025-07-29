"""
Dependency injection container for the bot.

This module provides a simple dependency injection system
to decouple services and improve testability.
"""

from typing import Any, Dict, Type, TypeVar

T = TypeVar('T')


class Container:
    """Simple dependency injection container."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
    
    def register(self, interface: Type[T], implementation: Any, singleton: bool = True) -> None:
        """
        Register a service implementation.
        
        Args:
            interface: Interface/type to register
            implementation: Implementation instance or factory
            singleton: Whether to use singleton pattern
        """
        key = self._get_key(interface)
        self._services[key] = implementation
        if singleton and key not in self._singletons:
            self._singletons[key] = implementation
    
    def get(self, interface: Type[T]) -> T:
        """
        Get service instance.
        
        Args:
            interface: Interface/type to resolve
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service not registered
        """
        key = self._get_key(interface)
        
        # Return singleton if exists
        if key in self._singletons:
            return self._singletons[key]
        
        # Get from services
        if key not in self._services:
            raise KeyError(f"Service {interface.__name__} not registered")
        
        service = self._services[key]
        
        # If it's a factory function, call it
        if callable(service) and not hasattr(service, '__module__'):
            service = service()
        
        return service
    
    def exists(self, interface: Type[T]) -> bool:
        """Check if service is registered."""
        key = self._get_key(interface)
        return key in self._services
    
    def _get_key(self, interface: Type[T]) -> str:
        """Get string key for interface."""
        return f"{interface.__module__}.{interface.__name__}"


# Global container instance
container = Container()


def get_service(interface: Type[T]) -> T:
    """Get service from global container."""
    return container.get(interface)


def register_service(interface: Type[T], implementation: Any, singleton: bool = True) -> None:
    """Register service in global container."""
    container.register(interface, implementation, singleton)