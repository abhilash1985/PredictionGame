from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.matches.data.question_bank import (
    bank_templates,
    create_match_question_pack,
    select_match_template_codes,
    sync_question_templates_from_bank,
)
from apps.matches.forms import AdminMatchPredictionForm, MatchPredictionForm
from apps.matches.models import GameSettings, Match, MatchQuestion, QuestionTemplate
from apps.tournaments.models import Round, Stadium, Team, Tournament

User = get_user_model()


class MatchPredictionFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='predictor@example.com', password='testpass123')
        tournament = Tournament.objects.create(
            name='Test WC',
            location='Test',
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            is_active=True,
        )
        rnd = Round.objects.create(tournament=tournament, name='Group A', sort_order=1)
        home = Team.objects.create(name='Home', short_name='HOM', fifa_code='HOM')
        away = Team.objects.create(name='Away', short_name='AWY', fifa_code='AWY')
        stadium = Stadium.objects.create(name='Test Stadium', city='Test City', country='Test')
        cls.match = Match.objects.create(
            tournament=tournament,
            round=rnd,
            match_number=1,
            team_home=home,
            team_away=away,
            stadium=stadium,
            kickoff_at=timezone.now() + timezone.timedelta(days=1),
        )
        template = QuestionTemplate.objects.create(
            code='MATCH_WINNER',
            question_text='Who wins?',
            default_points=8,
        )
        MatchQuestion.objects.create(
            match=cls.match,
            question_template=template,
            question_text='Who wins?',
            options=[home.name, away.name, 'Draw'],
            points=8,
        )
        settings = GameSettings.load()
        settings.tournament_active = tournament
        settings.save()

    def test_requires_match_and_user(self):
        with self.assertRaises(TypeError):
            MatchPredictionForm()

        with self.assertRaises(TypeError):
            MatchPredictionForm(match=self.match)

        form = MatchPredictionForm(match=self.match, user=self.user)
        self.assertIsNotNone(form)
        self.assertIn('point_booster', form.fields)

    def test_refunds_booster_when_unchecked(self):
        profile = self.user.profile
        profile.point_boosters_remaining = 2
        profile.save(update_fields=['point_boosters_remaining'])
        question = self.match.questions.first()

        form = MatchPredictionForm(
            {
                f'question_{question.id}': self.match.team_home.name,
                'point_booster': True,
            },
            match=self.match,
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        form = MatchPredictionForm(
            {
                f'question_{question.id}': self.match.team_home.name,
            },
            match=self.match,
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data['point_booster'])
        prediction = form.save()

        profile.refresh_from_db()
        self.assertFalse(prediction.point_booster_used)
        self.assertEqual(profile.point_boosters_remaining, 2)

    def test_point_booster_hidden_for_knockout(self):
        knockout_round = Round.objects.create(
            tournament=self.match.tournament,
            name='Round of 16',
            sort_order=99,
        )
        knockout_match = Match.objects.create(
            tournament=self.match.tournament,
            round=knockout_round,
            match_number=2,
            team_home=self.match.team_home,
            team_away=self.match.team_away,
            stadium=self.match.stadium,
            kickoff_at=timezone.now() + timezone.timedelta(days=2),
        )
        form = MatchPredictionForm(match=knockout_match, user=self.user)
        self.assertNotIn('point_booster', form.fields)
        self.assertFalse(knockout_match.is_group_stage)
        self.assertTrue(self.match.is_group_stage)


class PredictViewRedirectTests(MatchPredictionFormTests):
    def setUp(self):
        profile = self.user.profile
        profile.onboarding_completed = True
        profile.save(update_fields=['onboarding_completed'])
        self.client = Client()
        self.client.force_login(self.user)

    def test_redirects_to_match_list_when_from_matches(self):
        question = self.match.questions.first()
        url = reverse('match_predict', args=[self.match.pk])
        response = self.client.post(url, {
            f'question_{question.id}': self.match.team_home.name,
            'from': 'matches',
        })
        self.assertRedirects(response, reverse('match_list'), fetch_redirect_response=False)

    def test_redirects_to_dashboard_when_from_dashboard(self):
        question = self.match.questions.first()
        url = reverse('match_predict', args=[self.match.pk])
        response = self.client.post(url, {
            f'question_{question.id}': self.match.team_home.name,
            'from': 'dashboard',
        })
        self.assertRedirects(
            response,
            f"{reverse('dashboard')}?tab=matches",
            fetch_redirect_response=False,
        )

    def test_defaults_to_match_list_for_unknown_from(self):
        question = self.match.questions.first()
        url = reverse('match_predict', args=[self.match.pk])
        response = self.client.post(url, {
            f'question_{question.id}': self.match.team_home.name,
            'from': 'leaderboard',
        })
        self.assertRedirects(response, reverse('match_list'), fetch_redirect_response=False)


class ScorecardBackUrlTests(TestCase):
    def test_back_url_for_dashboard_stats(self):
        from apps.matches.views import _scorecard_back_url

        self.assertEqual(
            _scorecard_back_url('dashboard_stats'),
            f"{reverse('dashboard')}?tab=stats",
        )

    def test_back_url_for_dashboard_verdict_tab(self):
        from apps.matches.views import _scorecard_back_url

        self.assertEqual(
            _scorecard_back_url('dashboard', match_pk=42),
            f"{reverse('dashboard')}?tab=verdict&verdict_match=42",
        )

    def test_back_url_defaults_to_matches(self):
        from apps.matches.views import _scorecard_back_url

        self.assertEqual(_scorecard_back_url('matches'), reverse('match_list'))
        self.assertEqual(_scorecard_back_url('unknown'), reverse('match_list'))


class AdminMatchPredictionFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='admin-target@example.com', password='testpass123')
        tournament = Tournament.objects.create(
            name='Admin Test WC',
            location='Test',
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            is_active=True,
        )
        rnd = Round.objects.create(tournament=tournament, name='Group A', sort_order=1)
        home = Team.objects.create(name='Home', short_name='HOM', fifa_code='HOM')
        away = Team.objects.create(name='Away', short_name='AWY', fifa_code='AWY')
        stadium = Stadium.objects.create(name='Test Stadium', city='Test City', country='Test')
        cls.match = Match.objects.create(
            tournament=tournament,
            round=rnd,
            match_number=1,
            team_home=home,
            team_away=away,
            stadium=stadium,
            kickoff_at=timezone.now() - timezone.timedelta(hours=1),
        )
        template = QuestionTemplate.objects.create(
            code='MATCH_WINNER',
            question_text='Who wins?',
            default_points=8,
        )
        cls.question = MatchQuestion.objects.create(
            match=cls.match,
            question_template=template,
            question_text='Who wins?',
            options=[home.name, away.name, 'Draw'],
            points=8,
        )
        settings = GameSettings.load()
        settings.tournament_active = tournament
        settings.save()

    def test_shows_point_booster_for_group_stage_even_after_kickoff(self):
        form = AdminMatchPredictionForm(match=self.match, user=self.user)
        self.assertIn('point_booster', form.fields)

    def test_admin_can_enable_booster_without_remaining_count(self):
        profile = self.user.profile
        profile.point_boosters_remaining = 0
        profile.save(update_fields=['point_boosters_remaining'])

        form = AdminMatchPredictionForm(
            {
                f'question_{self.question.id}': self.match.team_home.name,
                'point_booster': True,
            },
            match=self.match,
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        prediction = form.save()

        profile.refresh_from_db()
        self.assertTrue(prediction.point_booster_used)
        self.assertEqual(profile.point_boosters_remaining, 0)

    def test_admin_refunds_booster_when_unchecked(self):
        profile = self.user.profile
        profile.point_boosters_remaining = 2
        profile.save(update_fields=['point_boosters_remaining'])

        form = AdminMatchPredictionForm(
            {
                f'question_{self.question.id}': self.match.team_home.name,
                'point_booster': True,
            },
            match=self.match,
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        form = AdminMatchPredictionForm(
            {
                f'question_{self.question.id}': self.match.team_home.name,
                'point_booster': False,
            },
            match=self.match,
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        prediction = form.save()

        profile.refresh_from_db()
        self.assertFalse(prediction.point_booster_used)
        self.assertEqual(profile.point_boosters_remaining, 2)


class QuestionBankTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='bank@example.com', password='testpass123')
        tournament = Tournament.objects.create(
            name='Bank Test WC',
            location='Test',
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            is_active=True,
        )
        rnd = Round.objects.create(tournament=tournament, name='Group A', sort_order=1)
        home = Team.objects.create(name='Home', short_name='HOM', fifa_code='HOM')
        away = Team.objects.create(name='Away', short_name='AWY', fifa_code='AWY')
        stadium = Stadium.objects.create(name='Test Stadium', city='Test City', country='Test')
        cls.match = Match.objects.create(
            tournament=tournament,
            round=rnd,
            match_number=99,
            team_home=home,
            team_away=away,
            stadium=stadium,
            kickoff_at=timezone.now() + timezone.timedelta(days=1),
        )
        settings = GameSettings.load()
        settings.tournament_active = tournament
        settings.save()
        sync_question_templates_from_bank()

    def test_bank_has_expected_template_count(self):
        self.assertEqual(len(bank_templates()), 141)

    def test_match_pack_has_seven_questions(self):
        codes = select_match_template_codes(self.match)
        self.assertEqual(len(codes), 7)
        self.assertEqual(codes[:3], ['MATCH_WINNER', 'HOME_GOALS', 'AWAY_GOALS'])

    def test_create_match_question_pack(self):
        created = create_match_question_pack(self.match)
        self.assertEqual(created, 7)
        self.assertEqual(self.match.questions.count(), 7)
        winner = self.match.questions.filter(question_template__code='MATCH_WINNER').first()
        self.assertEqual(winner.points, 10)
        self.assertIn('No Results', winner.options)


class MatchOrderingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        tournament = Tournament.objects.create(
            name='Order WC',
            location='Test',
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            is_active=True,
        )
        rnd = Round.objects.create(tournament=tournament, name='Group A', sort_order=1)
        stadium = Stadium.objects.create(name='Test Stadium', city='Test City', country='Test')
        home = Team.objects.create(name='Home', short_name='HOM', fifa_code='HOM')
        away = Team.objects.create(name='Away', short_name='AWY', fifa_code='AWY')
        cls.later_match = Match.objects.create(
            tournament=tournament,
            round=rnd,
            match_number=2,
            team_home=home,
            team_away=away,
            stadium=stadium,
            kickoff_at=timezone.now() + timezone.timedelta(days=2),
        )
        cls.earlier_match = Match.objects.create(
            tournament=tournament,
            round=rnd,
            match_number=1,
            team_home=away,
            team_away=home,
            stadium=stadium,
            kickoff_at=timezone.now() + timezone.timedelta(days=1),
        )
        settings = GameSettings.load()
        settings.tournament_active = tournament
        settings.save()

    def test_match_list_orders_by_match_number(self):
        client = Client()
        user = User.objects.create_user(email='order@example.com', password='testpass123')
        client.force_login(user)
        response = client.get(reverse('match_list'))
        numbers = list(response.context['matches'].values_list('match_number', flat=True))
        self.assertEqual(numbers, sorted(numbers))


class MatchKnockoutDisplayTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tournament = Tournament.objects.create(
            name='Knockout WC',
            location='Test',
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            is_active=True,
        )
        cls.round = Round.objects.create(tournament=cls.tournament, name='Round of 32', sort_order=20)
        cls.stadium = Stadium.objects.create(name='Test Stadium', city='Test City', country='Test')
        cls.home = Team.objects.create(name='Brazil', short_name='BRA', fifa_code='BRA')
        cls.away = Team.objects.create(name='Morocco', short_name='MAR', fifa_code='MAR')

    def test_penalty_score_display(self):
        match = Match.objects.create(
            tournament=self.tournament,
            round=self.round,
            match_number=73,
            team_home=self.home,
            team_away=self.away,
            stadium=self.stadium,
            kickoff_at=timezone.now() - timezone.timedelta(days=1),
            status=Match.Status.FINISHED,
            home_score=2,
            away_score=2,
            home_penalty_score=5,
            away_penalty_score=3,
            won_in=Match.WonIn.PEN,
        )
        self.assertEqual(match.display_home_score_line, '2(5)')
        self.assertEqual(match.display_away_score_line, '2(3)')
        self.assertEqual(match.winning_team, self.home)
        self.assertEqual(match.result_status_label, 'Penalties')

    def test_full_time_score_display_without_penalties(self):
        match = Match.objects.create(
            tournament=self.tournament,
            round=self.round,
            match_number=74,
            team_home=self.home,
            team_away=self.away,
            stadium=self.stadium,
            kickoff_at=timezone.now() - timezone.timedelta(days=1),
            status=Match.Status.FINISHED,
            home_score=2,
            away_score=1,
            won_in=Match.WonIn.FT,
        )
        self.assertEqual(match.display_home_score_line, '2')
        self.assertEqual(match.display_away_score_line, '1')
        self.assertEqual(match.winning_team, self.home)
