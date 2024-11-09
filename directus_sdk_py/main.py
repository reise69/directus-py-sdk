import sys

import requests
from urllib.parse import urljoin
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from typing import Dict, List, Union, Optional, Any
import os, json
from dataclasses import dataclass

import sqlparse
from sqlparse.sql import Where, Comparison, Identifier, Token
from sqlparse.tokens import Keyword

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
            urllib3.disable_warnings(category=InsecureRequestWarning)
        
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
        ).json()
        
        if 'errors' in auth:
            return {"errors": auth['errors'][0]['message']}

        auth = auth['data']
        
        self.static_token = None
        self.temporary_token = auth['access_token']
        self.refresh_token = auth['refresh_token']
        self.expires = auth['expires']
        return auth
    
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
            headers={"Authorization": f"Bearer {self.get_token()}"},
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
        auth = requests.post(
            f"{self.url}/auth/refresh",
            json={"refresh_token": refresh_token, 'mode': 'json'},
            verify=self.verify
        ).json()
        if "data" in auth:
            auth = auth['data']
            self.temporary_token = auth['access_token']
            self.refresh_token = auth['refresh_token']
            self.expires = auth['expires']
        else:
            raise Exception(auth)
        
        return auth

    def get_token(self):
        """
        Get the authentication token.

        Returns:
            str: The authentication token.
        """
        if self.static_token is not None:
            token = self.static_token
        elif self.temporary_token is not None:
            token = self.temporary_token
        else:
            token = ""
        return token

    
    def clean_url(self, domain: str, path: str) -> str:
        """
        Clean the URL by removing any leading slash.

        Args:
            path (str): The URL path.

        Returns:
            str: The cleaned URL path.
        """
        clean_path = urljoin(domain, path)
        clean_path = clean_path.replace("//", "/") if not clean_path.startswith("http://") and not clean_path.startswith("https://") and not clean_path.startswith("//") else clean_path
        return clean_path
        
    
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
            self.clean_url(self.url, path),
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
            self.clean_url(self.url, path),
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
        response = requests.request("SEARCH", self.clean_url(self.url, path), headers=headers, json=query, verify=self.verify,
                                    **kwargs)
       
        
        try:
            return response.json()['data']
        except Exception as e:
            return {'error': f'No data found for this request : {e}'}

    def delete(self, path, **kwargs):
        """
        Perform a DELETE request to the specified path.

        Args:
            path (str): The API endpoint path.
            **kwargs: Additional keyword arguments to pass to the request.
        """
        response = requests.delete(
            self.clean_url(self.url, path),
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
            self.clean_url(self.url, path),
            headers={"Authorization": f"Bearer {self.get_token()}"},
            verify=self.verify,
            **kwargs
        )

        if response.status_code not in [200, 204]:
            raise AssertionError(response.text)

        return response.json()

    def me(self):
        """
        Get the current user.

        Returns:
            dict: The user data.
        """
        return self.get("/users/me")
    
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
        Retrieve information about a file, not the way to download it

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

    def download_file(self, file_id: str, file_path: str) -> None:
        """
        Just download a directus file in local
        Args:
            file_id (str): The file ID.
            file_path (str): The path to save the file on your computer / server.
        """
        url = f"{self.url}/assets/{file_id}?download="
        headers = {"Authorization": f"Bearer {self.get_token()}"}
        response = requests.get(url, headers=headers)
    
        
        if response.status_code != 200:
            raise AssertionError(response.text)
        with open(file_path, "wb") as file:
            file.write(response.content)
    
    def download_photo(self, file_id: str, file_path: str, display: dict = {}, transform: list = []) -> None:
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

        if len(transform) > 0:
            display["transforms"] = json.dumps(transform)

        url = f"{self.url}/assets/{file_id}?download="
        headers = {"Authorization": f"Bearer {self.get_token()}"}
        response = requests.get(url, headers=headers, params=display, verify=self.verify)
        if response.status_code != 200:
            raise AssertionError(response.text)
        with open(file_path, "wb") as file:
            file.write(response.content)

    def get_url_file(self, file_id: str, display: dict = {}, transform: list = []) -> Union[str, bytes]:
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
    
    # Define the file type based on the file extension
    # return : image/jpeg, image/png, application/pdf, etc...
    def define_file_type(self, file_path: str) -> str:
        """
        Define the file type based on the file extension.
        """
        ext_file = file_path.split(".")[-1]
        if ext_file in ["jpg", "jpg"]:
            return "image/jpeg"
        elif ext_file in ["png", "webp", "gif"]:
            return f"image/{ext_file}"
        elif ext_file == "pdf":
            return "application/pdf"
        elif ext_file in ["doc", "docx"]:
            return "application/msword"
        elif ext_file in ["xls", "xlsx"]:
            return "application/vnd.ms-excel"
        elif ext_file == "odt":
            return "application/vnd.oasis.opendocument.text"
        elif ext_file == "ods":
            return "application/vnd.oasis.opendocument.spreadsheet"
        else:
            return "text/plain"
         #jpg, png, pdf, etc...
    
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
        # Mettre à jour les métadonnées du fichier
        data["type"] = self.define_file_type(file_path)
        if data and response.json()['data']:
            file_id = response.json()['data']['id']
            # Mettre à jour le type du fichier
            
            
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
        return self.get(f"/items/{collection_name}/{item_id}", **kwargs)

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

    def update_file(self, item_id, item_data, **kwargs):
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
        return self.patch(f"/files/{item_id}", json=item_data)
    
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
    
    def search_query(self, query: str, exclude_worlds_len: int = 2, cut_words: bool = True, **kwargs):
        q = []
        if cut_words:
            q = [word for word in query.split() if len(word) > exclude_worlds_len]
        else:
            q = [query]
            
        query = {
            "query": {
                "search": q
            }
        }
        return query
        
        
@dataclass
class DOp:
    EQUALS = "_eq"
    NOT_EQUALS = "_neq"
    LESS_THAN = "_lt"
    LESS_THAN_EQUAL = "_lte" 
    GREATER_THAN = "_gt"
    GREATER_THAN_EQUAL = "_gte"
    IN = "_in"
    NOT_IN = "_nin"
    NULL = "_null"
    NOT_NULL = "_nnull"
    CONTAINS = "_contains"
    NOT_CONTAINS = "_ncontains"
    STARTS_WITH = "_starts_with"
    ENDS_WITH = "_ends_with"
    BETWEEN = "_between"
    NOT_BETWEEN = "_nbetween"
    EMPTY = "_empty"
    NOT_EMPTY = "_nempty"

class DirectusQueryBuilder:
    def __init__(self):
        self.query = {"query": {}}
        
    def nested_condition(self, logic_op: str, conditions: List[Dict]) -> 'DirectusQueryBuilder':
        """
        Add nested logical conditions (_and/_or)
        Allows for complex nested conditions
        """
        if "filter" not in self.query["query"]:
            self.query["query"]["filter"] = {}
            
        # If we already have conditions, wrap everything in a new logical operator
        if self.query["query"]["filter"]:
            current_filter = self.query["query"]["filter"].copy()
            self.query["query"]["filter"] = {
                logic_op: [
                    current_filter,
                    *conditions
                ]
            }
        else:
            self.query["query"]["filter"][logic_op] = conditions
            
        return self
    
    def or_condition(self, conditions: List[Dict]) -> 'DirectusQueryBuilder':
        """Add OR conditions"""
        return self.nested_condition("_or", conditions)
    
    def and_condition(self, conditions: List[Dict]) -> 'DirectusQueryBuilder':
        """Add AND conditions"""
        return self.nested_condition("_and", conditions)
        
    def field(self, field_name: str, operator: str, value: Any) -> 'DirectusQueryBuilder':
        """Add a field filter condition"""
        condition = {field_name: {operator: value}}
        return self.and_condition([condition])

    def sort(self, *fields: str) -> 'DirectusQueryBuilder':
        """
        Add sort conditions. Use '-' prefix for descending order.
        Example:
            .sort('name', '-date_created') # Sort by name ASC, date_created DESC
        """
        if not fields:
            return self
            
        self.query["query"]["sort"] = list(fields)
        return self
    
    def limit(self, limit: int) -> 'DirectusQueryBuilder':
        """
        Set the maximum number of items to return
        Use -1 for maximum allowed items
        """
        self.query["query"]["limit"] = limit
        return self
    
    def offset(self, offset: int) -> 'DirectusQueryBuilder':
        """Set the number of items to skip"""
        self.query["query"]["offset"] = offset
        return self
        
    def page(self, page: int) -> 'DirectusQueryBuilder':
        """Set the page number (1-indexed)"""
        self.query["query"]["page"] = page
        return self
    
    def build(self) -> Dict:
        """Build and return the final query"""
        return self.query

class SQLToDirectusConverter:
    def __init__(self):
        self.builder = DirectusQueryBuilder()

    def _format_sql(self, sql: str) -> str:
        """Format SQL query before parsing"""
        # Add spaces around parentheses
        sql = sql.replace("(", " ( ")
        sql = sql.replace(")", " ) ")
        # Remove multiple spaces
        sql = " ".join(sql.split())
        return sql

    def _get_next_value_after_keyword(self, tokens: List[Token], keyword: str) -> Optional[str]:
        """Helper to get the next value after a keyword"""
        for i, token in enumerate(tokens):
            if token.ttype is Keyword and token.value.upper() == keyword:
                # Look for the next non-whitespace token
                for next_token in tokens[i+1:]:
                    if not next_token.is_whitespace:
                        return str(next_token)
        return None

    def _get_order_by_fields(self, tokens: List[Token]) -> List[str]:
        """
        Extrait les champs ORDER BY de la requête SQL
        Retourne une liste de champs avec '-' pour DESC
        """
        order_fields = []
        in_order_by = False
        
        for token in tokens:
            if token.ttype is Keyword and token.value.upper() == "ORDER BY":
                in_order_by = True
                continue
                    
            if in_order_by:
                if token.ttype is Keyword and token.value.upper() in ("LIMIT", "OFFSET"):
                    break
                    
                if not token.is_whitespace and token.value != ',':
                    value = str(token).strip()
                    if value.upper() == "ASC":
                        continue
                    elif value.upper() == "DESC":
                        if order_fields:  # S'assurer qu'il y a un champ précédent
                            order_fields[-1] = f"-{order_fields[-1]}"  # Ajouter le - au champ précédent
                    else:
                        order_fields.append(value)
                    
        return order_fields
    
    @staticmethod
    def _get_operator_mapping(sql_operator: str) -> str:
        """Map SQL operators to Directus operators"""
        mapping = {
            "=": DOp.EQUALS,
            "!=": DOp.NOT_EQUALS,
            "<": DOp.LESS_THAN,
            "<=": DOp.LESS_THAN_EQUAL,
            ">": DOp.GREATER_THAN,
            ">=": DOp.GREATER_THAN_EQUAL,
            "IN": DOp.IN,
            "NOT IN": DOp.NOT_IN,
            "IS NULL": DOp.NULL,
            "IS NOT NULL": DOp.NOT_NULL,
            "LIKE": DOp.CONTAINS,
        }
        return mapping.get(sql_operator.upper(), sql_operator)

    def _parse_comparison(self, comparison: Comparison) -> Dict:
        """Parse a SQL comparison into a Directus filter condition"""
        left = str(comparison.left)
        operator = None
        right_value = None

        # Parcourir les tokens pour trouver l'opérateur et la valeur
        for token in comparison.tokens:
            if token.is_whitespace:
                continue
            if token.ttype is sqlparse.tokens.Keyword:
                operator = self._get_operator_mapping(token.value)
            elif isinstance(token, sqlparse.sql.Parenthesis):
                # Cas spécial pour IN
                values = str(token).strip("()").split(",")
                right_value = [v.strip(" '\"") for v in values]
            elif token.ttype is sqlparse.tokens.Name.Mixed or token.ttype is sqlparse.tokens.String.Single:
                if right_value is None:  # Ne pas écraser la valeur si déjà définie (cas IN)
                    right_value = str(token).strip("'\"")

        if operator is None:
            # Cas où l'opérateur n'est pas un keyword (e.g., =, !=, etc.)
            operator = self._get_operator_mapping(str(comparison.token_next(0)[1]))

        return {left: {operator: right_value}}

    def _parse_group(self, group_token) -> Dict:
        """Parse a grouped condition token (conditions within parentheses) recursively"""
        # Remove outer parentheses and parse as a separate SQL statement
        group_sql = str(group_token).strip("()")
        if not group_sql.strip():
            return {}
            
        parsed_group = sqlparse.parse(group_sql)[0]
        
        conditions = []
        current_operator = "_and"
        
        # Pour gérer les IN on doit regrouper les tokens
        tokens = [token for token in parsed_group.tokens if not token.is_whitespace]
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            if token.ttype is Keyword:
                if token.value.upper() == "OR":
                    current_operator = "_or"
                elif token.value.upper() == "AND":
                    current_operator = "_and"
                i += 1
                continue
                
            # Détecter si c'est un IN
            if (i + 2) < len(tokens) and tokens[i+1].value.upper() == 'IN':
                # Créer une comparaison artificielle avec les 3 tokens
                comparison = Comparison([tokens[i], tokens[i+1], tokens[i+2]])
                cond = self._parse_comparison(comparison)
                if cond:
                    conditions.append(cond)
                i += 3  # On avance de 3 tokens
                continue
                
            if isinstance(token, Comparison):
                cond = self._parse_comparison(token)
                if cond:  # Ne pas ajouter les dictionnaires vides
                    conditions.append(cond)
            elif str(token).strip().startswith("("):
                # Parsing récursif pour les sous-groupes
                sub_conditions = self._parse_group(token)
                if sub_conditions:  # Ne pas ajouter les dictionnaires vides
                    conditions.append(sub_conditions)
            elif isinstance(token, sqlparse.sql.Parenthesis):
                if str(token).strip():  # Vérifier que ce n'est pas vide
                    sub_conditions = self._parse_group(token)
                    if sub_conditions:  # Ne pas ajouter les dictionnaires vides
                        conditions.append(sub_conditions)
            else:
                # Pour les tokens complexes, les redécouper
                sub_conditions = self._parse_non_standard_token(token)
                conditions.extend(sub_conditions)
                
            i += 1
        
        if not conditions:
            return {}
        if len(conditions) == 1:
            return conditions[0]
            
        return {current_operator: conditions}

    def _parse_non_standard_token(self, token) -> List[Dict]:
        """Parse a non-standard token by re-parsing it as SQL"""
        conditions = []
        try:
            sub_tokens = [t for t in sqlparse.parse(str(token))[0].tokens if not t.is_whitespace]
            i = 0
            while i < len(sub_tokens):
                sub_token = sub_tokens[i]
                
                # Détecter si c'est un IN
                if (i + 2) < len(sub_tokens) and sub_tokens[i+1].value.upper() == 'IN':
                    # Créer une comparaison artificielle avec les 3 tokens
                    comparison = Comparison([sub_tokens[i], sub_tokens[i+1], sub_tokens[i+2]])
                    parsed_condition = self._parse_comparison(comparison)
                    if parsed_condition:
                        conditions.append(parsed_condition)
                    i += 3  # On avance de 3 tokens
                    continue
                    
                if isinstance(sub_token, Comparison):
                    parsed_condition = self._parse_comparison(sub_token)
                    if parsed_condition:
                        conditions.append(parsed_condition)
                i += 1
        except Exception as e:
            print(f"Error in _parse_non_standard_token: {e}")
        return conditions

    def _parse_where_conditions(self, where_clause: Where) -> List[Dict]:
        """Parse WHERE clause conditions with support for groups"""
        conditions = []
        current_group = []
        current_operator = "_and"
        
        for token in where_clause.tokens:
            if token.is_whitespace:
                continue
                
            if token.ttype is Keyword and token.value.upper() in ("AND", "OR"):
                if token.value.upper() == "OR":
                    current_operator = "_or"
                continue
            
            if isinstance(token, Comparison):
                cond = self._parse_comparison(token)
                if cond:
                    conditions.append(cond)
            elif str(token).strip().startswith("("):
                group_conditions = self._parse_group(token)
                if group_conditions:
                    conditions.append(group_conditions)
            else:
                # Essayer de parser comme un token complexe
                sub_conditions = self._parse_non_standard_token(token)
                conditions.extend(sub_conditions)
        
        if current_operator == "_or":
            return [{"_or": conditions}]
        return conditions

    def convert(self, sql_query: str) -> Dict:
        """Convert a SQL query to a Directus query"""
        # Format SQL before parsing
        sql_query = self._format_sql(sql_query)
        
        parsed = sqlparse.parse(sql_query)[0]
        tokens = list(parsed.flatten())
        
        where_clause = None
        limit_value = None
        offset_value = None
        
        # Find WHERE clause
        for token in parsed.tokens:
            if isinstance(token, Where):
                where_clause = token
                break
        
        # Get LIMIT and OFFSET values
        limit_str = self._get_next_value_after_keyword(tokens, "LIMIT")
        offset_str = self._get_next_value_after_keyword(tokens, "OFFSET")
        
        if limit_str and limit_str.isdigit():
            limit_value = int(limit_str)
        if offset_str and offset_str.isdigit():
            offset_value = int(offset_str)
        
        # Build the query using DirectusQueryBuilder
        builder = DirectusQueryBuilder()
        
        # Add WHERE conditions if present
        if where_clause:
            conditions = self._parse_where_conditions(where_clause)
            builder.and_condition(conditions)
        
        # Add ORDER BY if present
        order_fields = self._get_order_by_fields(tokens)
        if order_fields:
            builder.sort(*order_fields)
        
        # Add limit and offset if present
        if limit_value is not None:
            builder.limit(limit_value)
        if offset_value is not None:
            builder.offset(offset_value)
            
        return builder.build()