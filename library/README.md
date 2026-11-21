# Library - Task 1 (Auth) + Task 2 (Book catalogue)

Run:
    docker compose up --build
Open: http://localhost:8080

Auth API:
  POST /api/auth/register  {name,email,password}
  POST /api/auth/login     {email,password}
  GET  /api/auth/me        (Bearer token)
  POST /api/auth/logout

Books API:
  GET  /api/books               list books
  POST /api/books/<id>/buy      (Bearer token)
  POST /api/books/<id>/borrow   (Bearer token)
