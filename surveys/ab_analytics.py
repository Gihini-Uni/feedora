"""
A/B analytics for the TWO-SURVEY (manual assignment) design.

Compares a gamified survey against a plain survey of identical content.
Each survey holds one condition's responses, so we compare across the two.

Usage:
    from .ab_analytics import compare_surveys
    result = compare_surveys(gamified_survey, plain_survey)
"""
from statistics import median, mean
from django.db.models import Avg
from .models import Response, Answer


# ── Timing helpers ────────────────────────────────────────────
def _durations_seconds(responses):
    """List of completion durations (seconds) for responses that have both timestamps."""
    out = []
    for r in responses:
        if r.started_at and r.completed_at:
            secs = (r.completed_at - r.started_at).total_seconds()
            if secs >= 0:                      # guard against clock weirdness
                out.append(secs)
    return out


def _fmt_duration(seconds):
    """Human-readable m s from a seconds value."""
    if not seconds:
        return "—"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}m {s}s" if m else f"{s}s"


# ── Per-survey stats ──────────────────────────────────────────
def survey_stats(survey, label):
    """Compute all metrics for one survey (one A/B condition)."""
    responses = Response.objects.filter(survey=survey)
    completed = responses.filter(completed_at__isnull=False)
    started   = responses.count()
    n_done    = completed.count()

    durations = _durations_seconds(completed)

    # Response quality — average length of free-text answers
    text_answers = Answer.objects.filter(
        response__survey=survey,
        question__question_type__in=['short', 'open'],
    ).exclude(text_value='')
    text_lengths = [len(a.text_value) for a in text_answers]

    return {
        'label':            label,
        'survey_title':     survey.title,
        'started':          started,
        'completed':        n_done,
        'completion_rate':  round(n_done / started * 100, 1) if started else 0.0,

        # timing
        'median_time_sec':  round(median(durations), 1) if durations else 0,
        'mean_time_sec':    round(mean(durations), 1)   if durations else 0,
        'median_time_disp': _fmt_duration(median(durations)) if durations else "—",
        'mean_time_disp':   _fmt_duration(mean(durations))   if durations else "—",
        'fastest_disp':     _fmt_duration(min(durations))    if durations else "—",
        'slowest_disp':     _fmt_duration(max(durations))    if durations else "—",
        '_durations':       durations,        # raw, for the significance test

        # engagement / quality
        'avg_points':       round(completed.aggregate(a=Avg('points_earned'))['a'] or 0, 1),
        'avg_text_len':     round(mean(text_lengths), 1) if text_lengths else 0,
    }


# ── Significance tests ────────────────────────────────────────
def _significance(a, b):
    """Run chi-square (completion) and Mann-Whitney (time). scipy optional."""
    out = {'p_completion': None, 'p_time': None, 'scipy_available': False, 'note': ''}
    try:
        from scipy.stats import chi2_contingency, mannwhitneyu
        out['scipy_available'] = True

        # Completion rate — 2x2 contingency (completed vs not) per group
        a_not = a['started'] - a['completed']
        b_not = b['started'] - b['completed']
        if a['started'] and b['started'] and (a['completed'] + b['completed']) > 0:
            table = [[a['completed'], a_not], [b['completed'], b_not]]
            try:
                _, p_c, _, _ = chi2_contingency(table)
                out['p_completion'] = round(float(p_c), 4)
            except Exception:
                pass

        # Completion time — Mann-Whitney U (non-parametric, good for small n)
        if len(a['_durations']) >= 2 and len(b['_durations']) >= 2:
            try:
                _, p_t = mannwhitneyu(a['_durations'], b['_durations'],
                                      alternative='two-sided')
                out['p_time'] = round(float(p_t), 4)
            except Exception:
                pass

    except ImportError:
        out['note'] = 'Install scipy for significance tests: pip install scipy'
    return out


def _interpret(p):
    """Plain-language verdict for a p-value, honest about small samples."""
    if p is None:
        return 'Not enough data'
    if p < 0.05:
        return 'Statistically significant (p < 0.05)'
    if p < 0.10:
        return 'Marginal / indicative trend (p < 0.10)'
    return 'Not statistically significant'


# ── Effect sizes (meaningful even with small n) ───────────────
def _effect_sizes(a, b):
    return {
        'completion_diff':  round(a['completion_rate'] - b['completion_rate'], 1),  # percentage points
        'median_time_diff': round((a['median_time_sec'] - b['median_time_sec']) / 60, 1),  # minutes
        'text_len_diff':    round(a['avg_text_len'] - b['avg_text_len'], 1),
        'points_diff':      round(a['avg_points'] - b['avg_points'], 1),
    }


# ── Main entry point ──────────────────────────────────────────
def compare_surveys(gamified_survey, plain_survey):
    """
    Compare two surveys (gamified vs plain).
    Returns a dict ready to hand to a template.
    """
    a = survey_stats(gamified_survey, 'Gamified')
    b = survey_stats(plain_survey,    'Plain')

    sig    = _significance(a, b)
    effect = _effect_sizes(a, b)

    total_n   = a['completed'] + b['completed']
    small_warn = (a['completed'] < 30 or b['completed'] < 30)

    return {
        'a':               a,
        'b':               b,
        'effect':          effect,
        'p_completion':    sig['p_completion'],
        'p_time':          sig['p_time'],
        'completion_verdict': _interpret(sig['p_completion']),
        'time_verdict':       _interpret(sig['p_time']),
        'scipy_available': sig['scipy_available'],
        'scipy_note':      sig['note'],
        'total_n':         total_n,
        'small_sample':    small_warn,
    }