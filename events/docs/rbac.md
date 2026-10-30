# RBAC usage (EMS-F-005)

Roles live in `events/roles.py`: `attendee`, `organizer`, `administrator`.
Public signup always gets `attendee`; only an admin can change a role.

**DRF API view**
```python
from events.permissions import IsOrganizer, IsEventOwner
class EventViewSet(ModelViewSet):
    permission_classes = [IsOrganizer, IsEventOwner]   # role + object ownership
```
**Template view**
```python
from events.decorators import role_required
@role_required(Role.ATTENDEE)
def my_registrations(request): ...
```
The main project settings use `events.authentication.EMSSessionAuthentication`
and `events.context_processors.rbac_context`. Administrator role changes are
handled through the event admin API and require a reason.

Responses: not logged in -> 401 (API) / login redirect (templates); wrong role or
not owner -> 403. Never read a role from request data. Hiding a button is not security.
