from apps.tournaments.models import Team


def configure_favorite_team_field(field):
    field.queryset = Team.objects.order_by('name')
    field.label_from_instance = lambda team: team.name
    field.empty_label = 'Select your favorite team'
