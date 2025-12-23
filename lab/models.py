from django.db import models
from content_management.models import ContentManager

class LabCategory(models.Model):
    """
    Category/Type mapping for Tests, Profiles, Packages
    """
    ENTITY_CHOICES = [
        ("lab_test", "Lab Test"),
        ("profile", "Profile"),
        ("package", "Package"),
    ]
    name = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=50, choices=ENTITY_CHOICES)
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("name", "entity_type")

    def __str__(self):
        return f"{self.entity_type}: {self.name}"


class LabTest(models.Model):
    name = models.CharField(max_length=255, unique=True)
    test_code = models.CharField(max_length=50, blank=True, null=True)
    # investigation = models.CharField(max_length=255,blank=True, null=True)
    sample_type = models.TextField( blank=True, null=True)
    temperature = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField( blank=True, null=True)
    special_instruction = models.TextField(blank=True, null=True)  # sample collection
    method = models.CharField(max_length=255, blank=True, null=True)
    reported_on = models.CharField(max_length=255, blank=True, null=True)
    
    category = models.ForeignKey(
        "LabCategory", on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={"entity_type": "test"}, related_name="lab_tests"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    # sample_required = models.CharField(max_length=255, blank=True, null=True)
    # image = models.ForeignKey(ContentManager, on_delete=models.SET_NULL, null=True, blank=True, related_name="lab_tests")
    child_tests = models.JSONField(
                                    default=list,
                                    blank=True,
                                    help_text="List of child tests"
                                )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.test_code} - {self.name}" if self.test_code else self.name



class Profile(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        LabCategory, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={"entity_type": "profile"}, related_name="profiles"
    )
    tests = models.ManyToManyField(LabTest, related_name="profiles")
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.ForeignKey(ContentManager, on_delete=models.SET_NULL, null=True, blank=True, related_name="profiles")

    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Package(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        LabCategory, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={"entity_type": "package"}, related_name="packages"
    )
    profiles = models.ManyToManyField(Profile, related_name="packages", blank=True)
    tests = models.ManyToManyField(LabTest, related_name="packages", blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.ForeignKey(ContentManager, on_delete=models.SET_NULL, null=True, blank=True, related_name="packages")

    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return self.name