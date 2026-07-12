from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_fsm import TransitionNotAllowed

from documents.models import Document
from drivers.models import DriverStatus


@receiver(post_save, sender=Document)
def suspend_driver_for_expired_license(sender, instance, **kwargs):
    if (
        instance.category == Document.Category.LICENSE
        and instance.driver
        and instance.is_expired
        and instance.driver.status != DriverStatus.SUSPENDED
    ):
        try:
            instance.driver.suspend()
            instance.driver.save(update_fields=["status", "updated_at"])
        except TransitionNotAllowed:
            return


@receiver(post_delete, sender=Document)
def delete_document_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
