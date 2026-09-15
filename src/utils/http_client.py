import requests
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HttpClient:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.session = self._create_session()
        self.default_timeout = self.config.get('timeout', 30)
        self.retry_count = self.config.get('retry_count', 3)
        self.retry_delay = self.config.get('retry_delay', 1)
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        ]
        self.current_ua_index = 0

    def _create_session(self) -> requests.Session:
        session = requests.Session()

        retry_strategy = Retry(
            total=self.retry_count,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20,
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_headers(self, custom_headers: Dict[str, str] = None) -> Dict[str, str]:
        headers = {
            'User-Agent': self.user_agents[self.current_ua_index % len(self.user_agents)],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

        if custom_headers:
            headers.update(custom_headers)

        self.current_ua_index += 1
        return headers

    def get(self, url: str, params: Dict[str, Any] = None,
            headers: Dict[str, str] = None, timeout: int = None) -> requests.Response:
        timeout = timeout or self.default_timeout
        headers = self._get_headers(headers)
        response = self.session.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response

    def post(self, url: str, data: Dict[str, Any] = None,
             json_data: Dict[str, Any] = None, headers: Dict[str, str] = None,
             timeout: int = None) -> requests.Response:
        timeout = timeout or self.default_timeout
        headers = self._get_headers(headers)

        if json_data:
            headers['Content-Type'] = 'application/json'
            response = self.session.post(url, json=json_data, headers=headers, timeout=timeout)
        else:
            response = self.session.post(url, data=data, headers=headers, timeout=timeout)

        response.raise_for_status()
        return response

    def close(self) -> None:
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()