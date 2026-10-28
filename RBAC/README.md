# RBAC module (EMS-F-005) - self-contained

Everything for issue #3 lives in this folder, so it cannot conflict with
teammates' files. Run all commands from inside `RBAC/`.

    cd RBAC
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py test

See docs/rbac.md for how other modules use the permission classes.
