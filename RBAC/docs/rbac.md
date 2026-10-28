# RBAC usage (EMS-F-005)

Roles live in `accounts/roles.py`: `attendee`, `organizer`, `administrator`.
Public signup always gets `attendee`; only an admin can change a role.

**DRF API view**
```python
from accounts.permissions import IsOrganizer, IsEventOwner
class EventViewSet(ModelViewSet):
    permission_classes = [IsOrganizer, IsEventOwner]   # role + object ownership
```
**Template view**
```python
from accounts.decorators import role_required
@role_required(Role.ATTENDEE)
def my_registrations(request): ...
```
Responses: not logged in -> 401 (API) / login redirect (templates); wrong role or
not owner -> 403. Never read a role from request data. Hiding a button is not security.
