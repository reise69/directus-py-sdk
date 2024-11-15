# Directus SDK for Python

[![PyPI version](https://badge.fury.io/py/directus-sdk-py.svg)](https://badge.fury.io/py/directus-sdk-py)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/pypi/pyversions/directus-sdk-py.svg)](https://pypi.org/project/directus-sdk-py/)

A Python SDK for interacting with Directus, an open-source headless CMS and API platform.

## About Directus

[Directus](https://directus.io/) is a powerful and flexible open-source headless CMS and API platform. It provides a
user-friendly interface for managing content and a robust API for integrating with other applications. Directus allows
you to create and customize your data models, manage users and permissions, and easily expose your data through a
RESTful API.

## About the library

This library provides a Python SDK for interacting with Directus. You can use it to perform various operations such as
managing users, files, collections, and items. The SDK simplifies the process of interacting with the Directus API by
providing a set of methods that you can use to perform common tasks.

## New features (1.1.0)

- Enhanced authentication handling with token expiration support
- New `me()` method to get current user information
- Improved file handling with automatic file type detection
- New `DirectusQueryBuilder` for constructing complex queries
- SQL to Directus query converter (`SQLToDirectusConverter`)
- Better error handling and response processing
- Enhanced image transformation capabilities
- Improved URL handling and cleaning

## Installation

You can install the Directus Python SDK using pip:

```bash
pip install directus-sdk-py
```

## Usage

Here are some examples of how to use the Directus Python SDK:

### Initialize the Client

```python
from directus_sdk_py import DirectusClient

client = DirectusClient(url='https://your-directus-instance.com', token='your_access_token')
```

### Authentication with email and password if needed

```python
# Login with email and password
client.login(email='user@example.com', password='password')

# Get current user information
me = client.me()

# Refresh token
client.refresh()

# Logout
client.logout()
```

### Users Management

```python
# Get all users
users = client.get_users()

# Create a new user
user_data = {
    'first_name': 'John',
    'last_name': 'Doe',
    'email': 'john@example.com',
    'password': 'password'
}
new_user = client.create_user(user_data)

# Update a user
updated_user = client.update_user(user_id='user_id', user_data={'first_name': 'Updated Name'})

# Delete a user
client.delete_user(user_id='user_id')
```

### Files Management

```python
# Get all files
files = client.get_files()

# Search files with a filter
request = {
    "query": {
        "filter": {
            "title": {
                "_icontains": "my search request" # Search for files with "my search request" in the title
            }
        }
    }
}
items = client.get_files(request)


# Suppose you get an item and it's a photo, you can get the URL of the photo with the following code
photo_url = client.get_file_url(items[0]['id'])

# It's possible to transform or add some display options to the photo URL
display = {
    "quality": 95, # Quality of the image
}
transform = [
    ["blur", 10], # Blur the image
    ["tint", "rgb(255, 0, 0)"] # Tint the image in red
]

photo_url = client.get_file_url(items[0]['id'], display=display, transform=transform)

# Download the file on the disk
client.download_photo(items[0]['id'], 'path/to/download.jpg', display=display, transform=transform)


# Download a file other than a photo
client.download_file(items[0]['id'], 'path/to/download.jpg')


# Upload a file
data = {
    "title": "Readme",
    "description": "Readme file",
    "tags": ['readme', 'file'],
}
file = client.upload_file("readme.md", data)

# Delete a file
client.delete_file(file_id='file_id')
```

Information about filter requests can be found in
the [Directus API documentation](https://docs.directus.io/reference/filter-rules.html)

### Collection and Item Management

```python
# Get a collection
collection = client.get_collection(collection_name='your_collection')

# List all items and filter the results
collection = "my_collection"
request = {
    "query": {
        # More information about filter requests can be found in the Directus API documentation (https://docs.directus.io/reference/filter-rules.html)
        "filter": {
            "col_name": {
                "_icontains": "inverness" # Search inverness in the col_name column
            }
        }
    }
}
items = client.get_items(collection, request)


# Get an item from a collection
item = client.get_item(collection_name='your_collection', item_id='item_id')

# Create a new item in a collection
item_data = {
    'title': 'New Item',
    'description': 'This is a new item'
}
new_item = client.create_item(collection_name='your_collection', item_data=item_data)

# Update an item in a collection
updated_item = client.update_item(collection_name='your_collection', item_id='item_id',
                                  item_data={'title': 'Updated Title'})

# Delete an item from a collection
client.delete_item(collection_name='your_collection', item_id='item_id')
```

## Using DirectusQueryBuilder

The new DirectusQueryBuilder provides a fluent interface for constructing complex queries:

```python
from directus_sdk_py import DirectusQueryBuilder, DOp

# Create a builder instance
builder = DirectusQueryBuilder()

# Build a complex query
query = (builder
    .field("status", DOp.EQUALS, "published")
    .or_condition([
        {"author": {DOp.EQUALS: "john"}},
        {"category": {DOp.IN: ["news", "tech"]}}
    ])
    .sort("date_created", "-title")
    .limit(10)
    .offset(0)
    .build())

# Use the query
items = client.get_items("articles", query)
```

## SQL to Directus Query Converter

For those like me, like to use SQL instead of Directus query language, you can use the `SQLToDirectusConverter` to convert your SQL queries to Directus query format:

```python
from directus_sdk_py import SQLToDirectusConverter

converter = SQLToDirectusConverter()

sql_query = """
SELECT * FROM articles
WHERE status = 'published'
AND (author = 'john' OR category IN ('news', 'tech'))
ORDER BY date_created ASC, title DESC
"""

directus_query = converter.convert(sql_query)
items = client.get_items("articles", directus_query)

```

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please:

- Fork the repository
- Create a new branch for your feature
- Submit a pull request

## License

This project is licensed under the MIT License.

## Acknowledgements

This library was inspired by the [directus-sdk-python](https://github.com/Jason-CKY/directus-sdk-python) project, which
is also released under the MIT License. Special thanks to the contributors of that project for their work.
