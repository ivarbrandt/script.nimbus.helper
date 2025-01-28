import requests

class BaseAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create and configure a requests session."""
        session = requests.Session()
        session.mount(self.base_url, requests.adapters.HTTPAdapter(pool_maxsize=100))
        return session