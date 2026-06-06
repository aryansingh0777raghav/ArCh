from abc import ABC, abstractmethod

class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, api_key: str = None) -> list:
        """
        Search the internet and return a list of results.
        Each result should be a dictionary:
        {
            "title": str,
            "url": str,
            "snippet": str
        }
        """
        pass
