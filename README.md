# Profile Management API

This is a practice project I am using to learn FastAPI and how to connect an API to a database.

The app lets me create, view, update, and delete profiles. Each profile has a username and an age.

## Tools used

- Python
- FastAPI for the API
- Pydantic for checking user input
- SQLAlchemy for working with the database
- SQLite for storing profiles
- Pytest for testing

## How to run the project

You need Python 3.10 or newer.

Clone the repository and open its folder:

```bash
git clone https://github.com/Attqawa20/My-fastapi.git
cd My-fastapi
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required packages:

```bash
python -m pip install -r requirements-dev.txt
```

Start the server:

```bash
python -m uvicorn registration_api:app --port 8002
```

Open this address in your browser:

http://127.0.0.1:8002/docs

You can test the endpoints there using **Try it out** and **Execute**.

Keep the server terminal open while testing. Press **Ctrl+C** when you want to stop it.

## Endpoints

| Method | Endpoint | What it does |
|---|---|---|
| POST | /profiles | Creates a profile |
| GET | /profiles | Shows profiles |
| GET | /profiles/{profile_id} | Shows one profile |
| PATCH | /profiles/{profile_id} | Updates a profile |
| DELETE | /profiles/{profile_id} | Deletes a profile |

## Example

To create a profile, send this to POST /profiles:

```json
{
  "username": "Ade",
  "age": 25
}
```

The response looks like this:

```json
{
  "id": 1,
  "username": "Ade",
  "age": 25
}
```

The database gives each profile an ID. Your ID may be different.

To change only the age, use PATCH with the profile's ID:

```json
{
  "age": 27
}
```

## Input rules

- Usernames must have 3 to 15 characters.
- Spaces at the beginning and end of usernames are removed.
- Duplicate usernames are not allowed. For example, Ade and ade count as the same username.
- Age must be a whole number greater than 0 and less than 120.

The list endpoint also accepts these query parameters:

| Parameter | Meaning | Rule |
|---|---|---|
| min_age | Only show profiles at or above this age | 0 to 119 |
| limit | Maximum number of profiles to return | 1 to 100 |
| offset | Number of matching profiles to skip | 0 or more |

For example:

```text
/profiles?min_age=30&limit=20&offset=0
```

I learned that `gt` means greater than, while `ge` means greater than or equal to.

## Database

Profiles are saved in a SQLite file called `profile_api.db`.

The app creates the database table when it starts. Saved profiles remain after the server stops and restarts.

## Testing

Run the automated tests with:

```bash
python -m pytest -q
```

My local result was **22 passed, 1 warning**. The warning was a dependency deprecation notice.

I also tested all five endpoints in Swagger, including:

- Creating and viewing profiles
- Updating only the age
- Filtering profiles by age
- Rejecting duplicate usernames
- Rejecting invalid usernames, ages, and query values
- Deleting a profile and checking that it returns 404 afterwards

## What I am learning

This project is helping me understand CRUD, request bodies, path parameters, query parameters, validation, and database operations.

It is a learning project for practice profiles. It does not include login or authentication, and it does not accept or store passwords.