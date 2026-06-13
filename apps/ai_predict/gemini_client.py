import json
import logging

from django.conf import settings

from apps.matches.models import GameSettings

logger = logging.getLogger(__name__)


class GeminiPredictor:
    SYSTEM_INSTRUCTION = (
        'You predict FIFA World Cup match questions for a fantasy prediction game. '
        'Return ONLY valid JSON. Every answer must exactly match one allowed option string. '
        'Use FIFA rankings, head-to-head, last 5 results, form vs similar-ranked opponents, '
        'group standings, the user favorite team, and the user recent predictions. '
        'NEVER choose "No Results" — always predict a real match outcome. '
        'Core questions (MATCH_WINNER, HOME_GOALS, AWAY_GOALS) MUST be logically consistent: '
        'home win means home goals > away goals; away win means away goals > home goals; '
        'Draw means home goals equals away goals. Pick realistic scorelines, not contradictory ones. '
        'For questions marked personalization=varied, choose different plausible answers per user '
        'based on user id, display name, and recent prediction style. '
        'Do not repeat identical varied answers for every user.'
    )

    @classmethod
    def is_configured(cls):
        game_settings = GameSettings.load()
        return bool(game_settings.ai_predict_enabled and settings.GOOGLE_API_KEY)

    @classmethod
    def predict(cls, context):
        if not cls.is_configured():
            return None

        prompt = cls._build_prompt(context)
        try:
            raw_text = cls._call_gemini(prompt)
            payload = json.loads(raw_text)
        except Exception:
            logger.exception('Gemini prediction failed for user=%s match=%s', context['user']['id'], context['match']['id'])
            return None

        answers = payload.get('answers') if isinstance(payload, dict) else None
        if not isinstance(answers, dict):
            logger.warning('Gemini returned invalid payload for user=%s match=%s', context['user']['id'], context['match']['id'])
            return None

        return answers

    @classmethod
    def _build_prompt(cls, context):
        return (
            f'{cls.SYSTEM_INSTRUCTION}\n\n'
            'Respond with JSON only in this shape:\n'
            '{"answers": {"<question_id>": "<exact option>", "...": "..."}}\n\n'
            f'Context:\n{json.dumps(context, indent=2, sort_keys=True)}'
        )

    @classmethod
    def _call_gemini(cls, prompt):
        from google import genai
        from google.genai import types

        game_settings = GameSettings.load()
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        response = client.models.generate_content(
            model=game_settings.ai_predict_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.65,
            ),
        )
        text = getattr(response, 'text', None)
        if not text:
            raise ValueError('Empty Gemini response')
        return text
