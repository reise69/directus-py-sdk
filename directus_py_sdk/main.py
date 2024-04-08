import sys

import requests
from urllib3.exceptions import InsecureRequestWarning
from typing import Dict, List, Union, Optional
import os, json


class DirectusClient:
    def __init__(self, url: str, token: str = None, email: str = None, password: str = None, verify: bool = False):
        """
        Initialize the DirectusClient.

        Args:
            url (str): The URL of the Directus instance.
            token (str): The static token for authentication (optional).
            email (str): The email for authentication (optional).
            password (str): The password for authentication (optional).
            verify (bool): Whether to verify SSL certificates (default: False).
        """
        self.verify = verify
        if not self.verify:
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

        self.url = url
        if token is not None:
            self.static_token = token
            self.temporary_token = None
        elif email is not None and password is not None:
            self.email = email
            self.password = password
            self.login(email, password)
            self.static_token = None
        else:
            self.static_token = None
            self.temporary_token = None

    def login(self, email: str = None, password: str = None) -> tuple:
        """
        Login with the /auth/login endpoint.

        Args:
            email (str): The email for authentication (optional).
            password (str): The password for authentication (optional).

        Returns:
            tuple: The access token and refresh token.
        """
        if email is None or password is None:
            email = self.email
            password = self.password
        else:
            self.email = email
            self.password = password

        auth = requests.post(
            f"{self.url}/auth/login",
            json={"email": email, "password": password},
            verify=self.verify
        ).json()['data']

        self.static_token = None
        self.temporary_token = auth['access_token']
        self.refresh_token = auth['refresh_token']

    def logout(self, refresh_token: str = None) -> None:
        """
        Logout using the /auth/logout endpoint.

        Args:
            refresh_token (str): The refresh token (optional).
        """
        if refresh_token is None:
            refresh_token = self.refresh_token
        requests.post(
            f"{self.url}/auth/logout",
            json={"refresh_token": refresh_token},
            verify=self.verify
        )
        self.temporary_token = None
        self.refresh_token = None

    def refresh(self, refresh_token: str = None) -> None:
        """
        Retrieve new temporary access token and refresh token.

        Args:
            refresh_token (str): The refresh token (optional).
        """
        if refresh_token is None:
            refresh_token = self.refresh_token
        auth = requests.post(
            f"{self.url}/auth/refresh",
            json={"refresh_token": refresh_token},
            verify=self.verify
        ).json()['data']

        self.temporary_token = auth['access_token']
        self.refresh_token = auth['refresh_token']

    def get_token(self):
        """
        Get the authentication token.

        Returns:
            str: The authentication token.
        """
        if self.static_token is not None:
            token = self.static_token
        elif self.temporary_token is not None:
            self.refresh()
            token = self.temporary_token
        else:
            token = ""
        return token

    def get(self, path, output_type: str = "json", **kwargs):
        """
        Perform a GET request to the specified path.

        Args:
            path (str): The API endpoint path.
            output_type (str): The output type (default: "json").
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            dict or str: The response data.
        """
        data = requests.get(
            f"{self.url}{path}",
            headers={"Authorization": f"Bearer {self.get_token()}"},
            verify=self.verify,
            **kwargs
        )
        if 'errors' in data.text:
            raise AssertionError(data.json()['errors'])
        if output_type == 'csv':
            return data.text

        return data.json()['data']

    def post(self, path, **kwargs):
        """
        Perform a POST request to the specified path.

        Args:
            path (str): The API endpoint path.
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            dict: The response data.
        """
        response = requests.post(
            f"{self.url}{path}",
            headers={"Authorization": f"Bearer {self.get_token()}"},
            verify=self.verify,
            **kwargs
        )
        if response.status_code != 200:
            raise AssertionError(response.text)

        return response.json()

    def search(self, path, query: Dict = None, **kwargs):
        """
        Perform a SEARCH request to the specified path.

        Args:
            path (str): The API endpoint path.
            query (dict): The search query parameters (optional).
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            dict: The response data.
        """
        headers = {"Authorization": f"Bearer {self.get_token()}"}
        response = requests.request("SEARCH", f"{self.url}{path}", headers=headers, json=query, verify=self.verify,
                                    **kwargs)

        return response.json()['data']

    def delete(self, path, **kwargs):
        """
        Perform a DELETE request to the specified path.

        Args:
            path (str): The API endpoint path.
            **kwargs: Additional keyword arguments to pass to the request.
        """
        response = requests.delete(
            f"{self.url}{path}",
            headers={"Authorization": f"Bearer {self.get_token()}"},
            verify=self.verify,
            **kwargs
        )
        if response.status_code != 204:
            raise AssertionError(response.text)

    def patch(self, path, **kwargs):
        """
        Perform a PATCH request to the specified path.

        Args:
            path (str): The API endpoint path.
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            dict: The response data.
        """
        response = requests.patch(
            f"{self.url}{path}",
            headers={"Authorization": f"Bearer {self.get_token()}"},
            verify=self.verify,
            **kwargs
        )

        if response.status_code not in [200, 204]:
            raise AssertionError(response.text)

        return response.json()

    def get_users(self, query: Dict = None, **kwargs):
        """
        Get users based on the provided query.

        Args:
            query (dict): The search query parameters (optional).
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            list: The list of users matching the query.
        """
        return self.search("/users", query=query, **kwargs)

    def create_user(self, user_data, **kwargs):
        """
        Create a new user.

        Args:
            user_data (dict): The user data.
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            dict: The created user.
        """
        return self.post("/users", json=user_data, **kwargs)

    def update_user(self, user_id, user_data, **kwargs):
        """
        Update a user.

        Args:
            user_id (str): The user ID.
            user_data (dict): The updated user data.
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            dict: The updated user.
        """
        return self.patch(f"/users/{user_id}", json=user_data, **kwargs)

    def delete_user(self, user_id, **kwargs):
        """
        Delete a user.

        Args:
            user_id (str): The user ID.
            **kwargs: Additional keyword arguments to pass to the request.
        """
        self.delete(f"/users/{user_id}", **kwargs)

    def get_files(self, query: Dict = None, **kwargs):
        """
        Get files based on the provided query.

        Args:
            query (dict): The search query parameters (optional).
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            list: The list of files matching the query.
        """
        return self.search("/files", query=query, **kwargs)

    def retrieve_file(self, file_id: str, **kwargs) -> Union[str, bytes]:
        """
        Retrieve a file.

        Args:
            file_id (str): The file ID.
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            str or bytes: The file content.
        """
        url = f"{self.url}/files/{file_id}"
        headers = {"Authorization": f"Bearer {self.get_token()}"}
        response = requests.get(url, headers=headers, verify=self.verify, **kwargs)
        if response.status_code != 200:
            raise AssertionError(response.text)
        return response.content

    def download_file(self, file_id: str, file_path: str, display: dict, transform: list) -> None:
        """
        Download a file from Directus.

        Args:
            file_id (str): The file ID.
            file_path (str): The path to save the file.
            display (dict): The parameters for displaying the file (size, quality, etc.).
            transform (dict): The parameters for transforming the file, add a parameter like : transforms=[
                    ["blur", 45],
                    ["tint", "rgb(255, 0, 0)"],
                    ["expand", { "right": 200, "bottom": 150 }]

        """

        """
        Transformations:
            fit — The fit of the thumbnail while always preserving the aspect ratio, can be any of the following options:
                cover — Covers both width/height by cropping/clipping to fit
                contain — Contain within both width/height using "letterboxing" as needed
                inside — Resize to be as large as possible, ensuring dimensions are less than or equal to the requested width and height
                outside — Resize to be as small as possible, ensuring dimensions are greater than or equal to the requested width and height
            width — The width of the thumbnail in pixels
            height — The height of the thumbnail in pixels
            quality — The optional quality of the thumbnail (1 to 100)
            withoutEnlargement — Disable image up-scaling
            format — What file format to return the thumbnail in. One of auto, jpg, png, webp, tiff
                auto — Will try to format it in webp or avif if the browser supports it, otherwise it will fallback to jpg.

        """

        if transform:
            display["transforms"] = json.dumps(transform)

        url = f"{self.url}/assets/{file_id}"
        headers = {"Authorization": f"Bearer {self.get_token()}"}
        response = requests.get(url, headers=headers, params=display, verify=self.verify)
        if response.status_code != 200:
            raise AssertionError(response.text)
        with open(file_path, "wb") as file:
            file.write(response.content)

    def get_url_file(self, file_id: str, display: dict, transform: list) -> Union[str, bytes]:
        """
        Retrieve a file.

        Args:
            file_id (str): The file ID.
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            str or bytes: The file content.
        """
        url = f"{self.url}/assets/{file_id}"

        # If there are display parameters
        if transform:
            # transformer en json
            display["transforms"] = json.dumps(transform)

        # Add parameters to the URL
        if display:
            url += "?"
            url += "&".join([f"{key}={value}" for key, value in display.items()])

        return url

    def upload_file(self, file_path: str, data: dict = {}) -> Dict:
        """
        Upload a file.

        Args:
            file_path (str): The path to the file.
            data (dict): The file metadata (optional).

        Returns:
            dict: The uploaded file data.
        """
        url = f"{self.url}/files"
        headers = {"Authorization": f"Bearer {self.get_token()}"}
        with open(file_path, 'rb') as file:
            files = {'file': file}
            response = requests.post(url, headers=headers, files=files, verify=self.verify)
        if response.status_code != 200:
            raise AssertionError(response.text)

        r = response.json()['data']
        # Update the file metadata
        if data and response.json()['data']:
            file_id = response.json()['data']['id']
            r = self.patch(f"/files/{file_id}", json=data)
            r = r['data']

        return r

    def delete_file(self, file_id, **kwargs):
        """
        Delete a file.

        Args:
            file_id (str): The file ID.
            **kwargs: Additional keyword arguments to pass to the request.
        """
        self.delete(f"/files/{file_id}", **kwargs)

    def get_collection(self, collection_name, **kwargs):
        """
        Get a collection.

        Args:
            collection_name (str): The collection name.
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            dict: The collection data.
        """
        return self.get(f"/collections/{collection_name}", **kwargs)

    def get_items(self, collection_name, query: Dict = None, **kwargs):
        """
        Get items from a collection based on the provided query.

        Args:
            collection_name (str): The collection name.
            query (dict): The search query parameters (optional).
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            list: The list of items matching the query.
        """
        return self.search(f"/items/{collection_name}", query=query, **kwargs)

    def get_item(self, collection_name, item_id, query: Dict = None, **kwargs):
        """
        Get a single item from a collection based on the provided query.

        Args:
            collection_name (str): The collection name.
            item_id (str): The item ID.
            query (dict): The search query parameters (optional).
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            dict: The item matching the query.
        """
        return self.search(f"/items/{collection_name}/{item_id}", query=query, **kwargs)

    def create_item(self, collection_name, item_data, **kwargs):
        """
        Create a new item in a collection.

        Args:
            collection_name (str): The collection name.
            item_data (dict): The item data.
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            dict: The created item.
        """
        return self.post(f"/items/{collection_name}", json=item_data, **kwargs)

    def update_item(self, collection_name, item_id, item_data, **kwargs):
        """
        Update an item in a collection.

        Args:
            collection_name (str): The collection name.
            item_id (str): The item ID.
            item_data (dict): The updated item data.
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            dict: The updated item.
        """
        return self.patch(f"/items/{collection_name}/{item_id}", json=item_data, **kwargs)

    def delete_item(self, collection_name, item_id, **kwargs):
        """
        Delete an item from a collection.

        Args:
            collection_name (str): The collection name.
            item_id (str): The item ID.
            **kwargs: Additional keyword arguments to pass to the request.
        """
        self.delete(f"/items/{collection_name}/{item_id}", **kwargs)

    def bulk_insert(self, collection_name: str, items: list, interval: int = 100, verbose: bool = False) -> None:
        """
        Insert multiple items into a collection in bulk.

        Args:
            collection_name (str): The collection name.
            items (list): The list of items to insert.
            interval (int): The number of items to insert per request (default: 100).
            verbose (bool): Whether to print progress information (default: False).
        """
        length = len(items)
        for i in range(0, length, interval):
            if verbose:
                print(f"Inserting {i}-{min(i + interval, length)} out of {length}")
            self.post(f"/items/{collection_name}", json=items[i:i + interval])

    def duplicate_collection(self, collection_name: str, duplicate_collection_name: str) -> None:
        """
        Duplicate a collection with its schema, fields, and data.

        Args:
            collection_name (str): The name of the collection to duplicate.
            duplicate_collection_name (str): The name of the duplicated collection.
        """
        duplicate_collection = self.get(f"/collections/{collection_name}")
        duplicate_collection['collection'] = duplicate_collection_name
        duplicate_collection['meta']['collection'] = duplicate_collection_name
        duplicate_collection['schema']['name'] = duplicate_collection_name
        self.post("/collections", json=duplicate_collection)

        fields = [field for field in self.get_all_fields(collection_name) if not field['schema']['is_primary_key']]
        for field in fields:
            self.post(f"/fields/{duplicate_collection_name}", json=field)

        items = self.get(f"/items/{collection_name}", params={"limit": -1})
        self.bulk_insert(duplicate_collection_name, items)

    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists in Directus.

        Args:
            collection_name (str): The collection name.

        Returns:
            bool: True if the collection exists, False otherwise.
        """
        collection_schema = [col['collection'] for col in self.get('/collections')]
        return collection_name in collection_schema

    def delete_all_items(self, collection_name: str) -> None:
        """
        Delete all items from a collection.

        Args:
            collection_name (str): The collection name.
        """
        pk_name = self.get_pk_field(collection_name)['field']
        item_ids = [data['id'] for data in self.get(f"/items/{collection_name}?fields={pk_name}", params={"limit": -1})]
        if not item_ids:
            raise AssertionError("No items to delete!")

        for i in range(0, len(item_ids), 100):
            self.delete(f"/items/{collection_name}", json=item_ids[i:i + 100])

    def get_all_fields(self, collection_name: str, query: Dict = None, **kwargs) -> list:
        """
        Get all fields of a collection based on the provided query.

        Args:
            collection_name (str): The collection name.
            query (dict): The search query parameters (optional).
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            list: The list of fields matching the query.
        """
        fields = self.search(f"/fields/{collection_name}", query=query, **kwargs)
        for field in fields:
            if field.get('meta') and field['meta'].get('id'):
                field['meta'].pop('id')

        return fields

    def get_pk_field(self, collection_name: str) -> dict:
        """
        Get the primary key field of a collection.

        Args:
            collection_name (str): The collection name.

        Returns:
            dict: The primary key field.
        """
        return next(field for field in self.get(f"/fields/{collection_name}") if field['schema']['is_primary_key'])

    def get_all_user_created_collection_names(self, query: Dict = None, **kwargs) -> list:
        """
        Get all user-created collection names based on the provided query.

        Args:
            query (dict): The search query parameters (optional).
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            list: The list of user-created collection names matching the query.
        """
        collections = self.search('/collections', query=query, **kwargs)
        return [col['collection'] for col in collections if not col['collection'].startswith('directus')]

    def get_all_fk_fields(self, collection_name: str, query: Dict = None, **kwargs) -> list:
        """
        Get all foreign key fields of a collection based on the provided query.

        Args:
            collection_name (str): The collection name.
            query (dict): The search query parameters (optional).
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            list: The list of foreign key fields matching the query.
        """
        fields = self.search(f"/fields/{collection_name}", query=query, **kwargs)
        return [field for field in fields if field['schema'].get('foreign_key_table')]

    def get_relations(self, collection_name: str, query: Dict = None, **kwargs) -> list:
        """
        Get all relations of a collection based on the provided query.

        Args:
            collection_name (str): The collection name.
            query (dict): The search query parameters (optional).
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            list: The list of relations matching the query.
        """
        relations = self.search(f"/relations/{collection_name}", query=query, **kwargs)
        return [{
            "collection": relation["collection"],
            "field": relation["field"],
            "related_collection": relation["related_collection"]
        } for relation in relations]

    def post_relation(self, relation: dict) -> None:
        """
        Create a new relation.

        Args:
            relation (dict): The relation data.
        """
        assert set(relation.keys()) == {'collection', 'field', 'related_collection'}
        try:
            self.post(f"/relations", json=relation)
        except AssertionError as e:
            if '"id" has to be unique' in str(e):
                self.post_relation(relation)
            else:
                raise

