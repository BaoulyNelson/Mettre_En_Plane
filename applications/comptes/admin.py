from django.contrib import admin

from .models import ConfigurationSite, ProfilUtilisateur


@admin.register(ProfilUtilisateur)
class ProfilUtilisateurAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "telephone")
    search_fields = ("utilisateur__username", "utilisateur__email", "telephone")


@admin.register(ConfigurationSite)
class ConfigurationSiteAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ConfigurationSite.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
