MASK_ROLE_NAME = "Phlebo"


def mask_mobile(mobile):
    """Mask the middle 5 characters of a mobile number, e.g. 8001234567 -> 80xxxxx67."""
    if not mobile or len(mobile) < 6:
        return mobile

    length = len(mobile)
    if length <= 5:
        return "x" * length

    prefix_len = (length - 5) // 2
    suffix_len = length - 5 - prefix_len
    prefix = mobile[:prefix_len]
    suffix = mobile[length - suffix_len:] if suffix_len else ""
    return f"{prefix}{'x' * 5}{suffix}"


def should_mask_mobile_for(request, target_user):
    """True if `request`'s caller is a Phlebo and `target_user` isn't the caller themself."""
    if request is None:
        return False

    caller = getattr(request, "user", None)
    if not caller or not getattr(caller, "is_authenticated", False):
        return False

    role = getattr(caller, "role", None)
    if not role or role.name != MASK_ROLE_NAME:
        return False

    if target_user is not None and target_user.pk == caller.pk:
        return False

    return True
