import json
import json as json_lib
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Survey, Question, MCQOption, Response, Answer
from .hmsam import HMSAM_QUESTIONS
from django.db import transaction
from django.core.mail import send_mail
from accounts.models import RespondentProfile
from accounts.utils import get_level_info
from django.utils import timezone
from datetime import datetime
from .ab_analytics import compare_surveys
from accounts.utils import get_badges, get_level_info


@login_required
def survey_type_select(request):
    return render(request, 'surveys/survey_type_select.html')


@login_required
def create_survey(request, survey_type):
    is_hmsam = (survey_type == 'hmsam')
    if request.method == 'POST':
        data   = json.loads(request.body)
        action = data.get('action', 'publish')  # 'draft' or 'publish'

        survey = Survey.objects.create(
            organization=request.user,
            title=data.get('title', 'Untitled Survey'),
            description=data.get('description', ''),
            is_hmsam=is_hmsam,
            is_draft=(action == 'draft'),
            is_active=(action == 'publish'),
            theme_accent=data.get('theme_accent', '#14140f'),
            theme_bg=data.get('theme_bg', '#fafaf7'),
            submit_label=data.get('submit_label', 'Submit'),
            header_image_b64=data.get('header_image', ''),
            btn_color=data.get('btn_color', '#14140f'),
            btn_radius=data.get('btn_radius', '6'),
            btn_padding=data.get('btn_padding', '10px 22px'),
            btn_font_size=data.get('btn_font_size', '14px'),
            q_font=data.get('q_font', "'Inter',sans-serif"),
            header_font=data.get('header_font', "'Instrument Serif',serif"),
        )

        for i, q in enumerate(data.get('questions', [])):
            question = Question.objects.create(
                survey=survey,
                text=q.get('text', ''),
                code=q.get('code', ''),
                question_type=q.get('type', 'likert'),
                hmsam_construct=q.get('construct', '') or None,
                order=i,
                is_required=q.get('required', True),
                rating_style=q.get('ratingStyle', 'stars'),
                rating_max=int(q.get('ratingMax', 5)),
                section_title=q.get('sectionTitle', ''),
                section_num=int(q.get('sectionNum', 1)),
            )
            for j, opt_text in enumerate(q.get('options', [])):
                MCQOption.objects.create(question=question, text=opt_text, order=j)

        if action == 'draft':
            return JsonResponse({'redirect': f'/surveys/{survey.access_uuid}/features/'})
        else:
            return JsonResponse({
                'status':        'created',
                'dashboard_url': f'/surveys/{survey.access_uuid}/dashboard/',
            })

    hmsam_questions_json = json.dumps([
        {'text': text, 'code': code, 'type': 'likert', 'construct': construct, 'required': True}
        for construct, code, text in HMSAM_QUESTIONS
    ]) if is_hmsam else '[]'

    return render(request, 'surveys/survey_builder.html', {
        'is_hmsam': is_hmsam,
        'survey_type': survey_type,
        'hmsam_questions_json': hmsam_questions_json,
    })



@login_required
def my_surveys(request):
    surveys = Survey.objects.filter(organization=request.user).order_by('-created_at')
    return render(request, 'surveys/my_surveys.html', {'surveys': surveys})


@login_required
def survey_dashboard(request, uid):
    survey         = get_object_or_404(Survey, access_uuid=uid, organization=request.user)
    responses      = Response.objects.filter(survey=survey).order_by('-completed_at')
    response_count = responses.count()
 
    # Cronbach's alpha
    alpha, alpha_interp = None, 'Not enough data'
    try:
        from .analytics import cronbach_alpha as calc_alpha
        alpha, alpha_interp = calc_alpha(survey)
    except Exception:
        pass
 
    # HMSAM (only for HMSAM surveys)
    hmsam_scores        = None
    overall_score       = None
    overall_interp      = None
    if survey.is_hmsam:
        try:
            from .analytics import get_hmsam_scores, get_overall_interpretation
            hmsam_scores, overall_score = get_hmsam_scores(survey)
            if overall_score:
                overall_interp = get_overall_interpretation(overall_score)
        except Exception:
            pass
 
    # Response distribution for charts
    distribution      = []
    distribution_json = '[]'
    try:
        from .analytics import get_response_distribution
        distribution = get_response_distribution(survey)
        distribution_json = json_lib.dumps([
            {
                'question_id': str(item['question_id']),
                'question':    item['text'],
                'type':        item['type'],
                'data':        item['data'] if item['type'] not in ['short','open'] else [],
                'word_freq':   item.get('word_freq', {}),
                'texts':       item.get('texts', []),
            }
            for item in distribution
        ])
    except Exception:
        pass
 
    # Leaderboard
    leaderboard = []
    try:
        from .analytics import get_leaderboard
        leaderboard = get_leaderboard(survey)
    except Exception:
        pass
 
    # For by-respondent tab
    respondent_list = responses.select_related('user')
 
    # Selected respondent answers
    selected_response    = None
    respondent_answers   = []
    selected_response_id = request.GET.get('response_id')
    if selected_response_id:
        try:
            from .analytics import get_respondent_answers
            selected_response  = Response.objects.get(
                id=selected_response_id, survey=survey
            )
            respondent_answers = get_respondent_answers(selected_response)
        except Response.DoesNotExist:
            pass

    # ── Per-question point values ──────────────────────────────
    questions      = list(survey.questions.all().order_by('order'))
    features       = survey.features or {}
    points_config  = features.get('points', {})
    point_values   = points_config.get('values', {})
    DEFAULT_POINTS = {'likert':10,'rating':10,'mcq':10,'checkbox':10,
                      'dropdown':10,'short':10,'open':20,'date':5,'file':15}
    for q in questions:
        q.point_value = point_values.get(
            q.question_type, DEFAULT_POINTS.get(q.question_type, 10)
        )
    points_enabled = points_config.get('enabled', False)
        

    return render(request, 'surveys/dashboard.html', {
        'survey':              survey,
        'questions':           questions,
        'points_enabled':      points_enabled,
        'response_count':      response_count,
        'responses':           responses[:20],
        'respondent_list':     respondent_list,
        'selected_response':   selected_response,
        'respondent_answers':  respondent_answers,
        'alpha':               alpha,
        'alpha_interp':        alpha_interp,
        'distribution':        distribution,
        'distribution_json':   distribution_json,
        'leaderboard':         leaderboard,
        'hmsam_scores':        hmsam_scores,
        'overall_score':       overall_score,
        'overall_interp':      overall_interp,
    })
 


@login_required
def export_csv(request, uid):
    survey = get_object_or_404(Survey, access_uuid=uid, organization=request.user)
    try:
        from .analytics import csv_export
        csv_data = csv_export(survey)
    except Exception as e:
        return HttpResponse(f'Error generating CSV: {e}', status=500)
    response = HttpResponse(csv_data, content_type='text/csv')
    filename = survey.title.replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}_responses.csv"'
    return response


def survey_preview(request):
    return render(request, 'surveys/survey_preview.html')


# ── Respondent views — public, no login required ────────────

def access_survey(request):
    error, submitted_code = None, ''
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        submitted_code = code
        if not code:
            error = 'Please enter an access code.'
        else:
            try:
                survey = Survey.objects.get(access_code=code, is_active=True)
                return redirect('respond_survey', uid=survey.access_uuid)
            except Survey.DoesNotExist:
                error = 'Invalid code. Please check and try again.'
    return render(request, 'surveys/access.html', {'error': error, 'submitted_code': submitted_code})



def submit_response(request, uid):
    if request.method != 'POST':
        return redirect('respond_survey', uid=uid)

    survey = get_object_or_404(Survey, access_uuid=uid, is_active=True)
    user = request.user if request.user.is_authenticated else None

    # Enforce "limit to 1 response per user" (registered users only)
    limit_one = (survey.features or {}).get('collection', {}).get('limit', False)
    if limit_one and user and Response.objects.filter(survey=survey, user=user).exists():
        return render(request, 'surveys/already_responded.html', {'survey': survey})

    # Timing: read start time from session
    start_iso  = request.session.get(f'start_{survey.id}')
    started_at = datetime.fromisoformat(start_iso) if start_iso else None

    # Read custom point values from survey features 
    features       = survey.features or {}
    points_config  = features.get('points', {})
    points_enabled = points_config.get('enabled', False)
    custom_values  = points_config.get('values', {})

    DEFAULT_POINTS = {
        'likert': 10, 'rating': 10, 'mcq': 10, 'checkbox': 10,
        'dropdown': 10, 'short': 10, 'open': 20, 'date': 5, 'file': 15,
    }

    def pts(qtype, answer_text=''):
        if not points_enabled:
            return 0
        base = custom_values.get(qtype, DEFAULT_POINTS.get(qtype, 10))
        if qtype in ('short', 'open') and len(answer_text) > 20:
            base = custom_values.get('open', DEFAULT_POINTS['open'])
        return base

    # ── Create the Response ONCE, with started_at ──
    response_obj = Response.objects.create(
        survey=survey,
        user=user,
        points_earned=0,
        started_at=started_at,
    )
    total_points = 0

    for question in survey.questions.all().order_by('order'):
        key = f'q_{question.id}'

        if question.question_type == 'likert':
            val = request.POST.get(key)
            if val and val.isdigit() and 1 <= int(val) <= 5:
                Answer.objects.create(response=response_obj, question=question, likert_value=int(val))
                total_points += pts('likert')

        elif question.question_type in ['short', 'open']:
            val = request.POST.get(key, '').strip()
            if val:
                Answer.objects.create(response=response_obj, question=question, text_value=val)
                total_points += pts(question.question_type, val)

        elif question.question_type == 'mcq':
            val = request.POST.get(key)
            if val:
                try:
                    option = MCQOption.objects.get(id=int(val), question=question)
                    Answer.objects.create(response=response_obj, question=question, selected_option=option)
                    total_points += pts('mcq')
                except (MCQOption.DoesNotExist, ValueError):
                    pass

        elif question.question_type == 'checkbox':
            vals = request.POST.getlist(key)
            for val in vals:
                try:
                    option = MCQOption.objects.get(id=int(val), question=question)
                    Answer.objects.create(response=response_obj, question=question, selected_option=option)
                except (MCQOption.DoesNotExist, ValueError):
                    pass
            if vals:
                total_points += pts('checkbox')

        elif question.question_type == 'dropdown':
            val = request.POST.get(key)
            if val:
                try:
                    option = MCQOption.objects.get(id=int(val), question=question)
                    Answer.objects.create(response=response_obj, question=question, selected_option=option)
                    total_points += pts('dropdown')
                except (MCQOption.DoesNotExist, ValueError):
                    pass

        elif question.question_type == 'rating':
            val = request.POST.get(key)
            if val and val.isdigit():
                Answer.objects.create(response=response_obj, question=question, likert_value=int(val))
                total_points += pts('rating')

        elif question.question_type == 'date':
            val = request.POST.get(key, '').strip()
            if val:
                Answer.objects.create(response=response_obj, question=question, text_value=val)
                total_points += pts('date')

    response_obj.points_earned = total_points
    response_obj.save()

    if user:
        profile, _ = RespondentProfile.objects.get_or_create(user=user)
        old_total  = profile.total_points
        new_total  = old_total + total_points

        old_level = get_level_info(old_total)['level']
        new_level = get_level_info(new_total)['level']

        profile.total_points = new_total
        profile.save(update_fields=['total_points'])

        if new_level > old_level:
            info = get_level_info(new_total)
            send_mail(
                subject=f'You reached Level {new_level} — {info["title"]}!',
                message=(
                    f'Congratulations!\n\n'
                    f'You have reached Level {new_level}: {info["title"]} on Feedora.\n\n'
                    f'Total points: {new_total}\n\n'
                    f'Keep participating in surveys to reach the next level.\n\n'
                    f'Thank you for contributing to research.\n'
                    f'The Feedora Team'
                ),
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True,
            )


    earned_badge = None
    show_badge = (survey.features or {}).get('badges', {}).get('show_earned', False)
    if show_badge and user and user.is_authenticated:
        earned, _ = get_badges(new_total)      # new_total = their cumulative points
        level_info = get_level_info(new_total)
        if earned:
            earned_badge = {
                'name':  earned['name'],
                'image': earned['image'],
                'title': level_info['title'],
            }

    return render(request, 'surveys/thank_you.html', {
        'survey': survey,
        'points': total_points,
        'earned_badge': earned_badge,
    })

# This is the latest add_featutres part

@login_required
def add_features(request, uid):
    survey = get_object_or_404(Survey, access_uuid=uid, organization=request.user)
 
    if request.method == 'POST':
        data     = json.loads(request.body)
        action   = data.get('action', 'save')
        features = data.get('features', {})
 
        survey.features = features
 
        # Sync accept responses with is_active
        collection = features.get('collection', {})
        if 'accept' in collection:
            survey.is_active = bool(collection['accept'])
 
        if action == 'publish':
            survey.is_draft  = False
            survey.is_active = True
            survey.save()
            return JsonResponse({
                'status': 'created',
                'dashboard_url': f'/surveys/{survey.access_uuid}/dashboard/',
            })
        else:
            survey.save()
            return JsonResponse({'status': 'ok'})
 
    # GET — pass fresh survey object so template reads latest features
    survey.refresh_from_db()
    return render(request, 'surveys/add_features.html', {
        'survey': survey,
        'features_json': json.dumps(survey.features or {}),
    })

def respond_survey(request, uid):
    survey = get_object_or_404(Survey, access_uuid=uid, is_active=True)
    
    # Already-responded guard (registered users only)
    limit_one = (survey.features or {}).get('collection', {}).get('limit', False)
    if limit_one and request.user.is_authenticated and \
       Response.objects.filter(survey=survey, user=request.user).exists():
        return render(request, 'surveys/already_responded.html', {'survey': survey})
    
    start_key = f'start_{survey.id}'
    if start_key not in request.session:
        request.session[start_key] = timezone.now().isoformat()
    questions_qs = survey.questions.all().order_by('order')
    questions    = []
    seen_sections = set()
 
    for q in questions_qs:
        q.rating_range = range(1, (q.rating_max or 5) + 1)
        if not q.rating_style or q.rating_style not in ('stars', 'numeric', 'likert'):
            q.rating_style = 'stars'
        q.show_section_header = False
        if q.section_title:
            if q.section_title not in seen_sections:
                q.show_section_header = True
                seen_sections.add(q.section_title)
        elif q.section_num and q.section_num > 1:
            key = f'sec_{q.section_num}'
            if key not in seen_sections:
                q.show_section_header = True
                seen_sections.add(key)
        questions.append(q)
 
    # Get features with defaults
    features = survey.features or {}
    points_config = features.get('points', {})
    point_values  = points_config.get('values', {})
    mascot_enabled = features.get('mascot', {}).get('enabled', False)

    DEFAULT_POINTS = {
        'likert':10, 'rating':10, 'mcq':10, 'checkbox':10,
        'dropdown':10, 'short':10, 'open':20, 'date':5, 'file':15,
    }

    # Attach the point value to each question for template display
    for q in questions:
        q.point_value = point_values.get(q.question_type, DEFAULT_POINTS.get(q.question_type, 10))
 
    return render(request, 'surveys/respond.html', {
        'survey': survey,
        'questions': questions,
        'mascot_enabled': mascot_enabled,
        'mascot_position': features.get('mascot', {}).get('position', 'bottom-left'),
    })

@login_required
def edit_survey(request, uid):
    survey = get_object_or_404(Survey, access_uuid=uid, organization=request.user)

    if request.method == 'POST':
        data   = json.loads(request.body)
        action = data.get('action', 'draft')

        # Update the existing survey instead of creating a new one
        survey.title  = data.get('title', survey.title)
        survey.description = data.get('description', survey.description)
        survey.theme_accent = data.get('theme_accent', survey.theme_accent)
        survey.theme_bg = data.get('theme_bg', survey.theme_bg)
        survey.submit_label = data.get('submit_label', survey.submit_label)
        survey.header_image_b64 = data.get('header_image', survey.header_image_b64)
        survey.btn_color = data.get('btn_color', survey.btn_color)
        survey.btn_radius = data.get('btn_radius', survey.btn_radius)
        survey.btn_padding = data.get('btn_padding', survey.btn_padding)
        survey.btn_font_size = data.get('btn_font_size', survey.btn_font_size)
        survey.q_font = data.get('q_font', survey.q_font)
        survey.header_font = data.get('header_font', survey.header_font)

        if action == 'publish':
            survey.is_draft  = False
            survey.is_active = True

        survey.save()

        # ── Update questions WITHOUT destroying existing answers ──
        incoming = data.get('questions', [])

        with transaction.atomic():
            kept_ids    = []

            for i, q in enumerate(incoming):
                q_id = q.get('id')  # existing question PK, if any

                if q_id:
                    # UPDATE existing question — answers stay intact
                    try:
                        question = Question.objects.get(id=q_id, survey=survey)
                    except Question.DoesNotExist:
                        question = None
                else:
                    question = None

                if question:
                    question.text            = q.get('text', '')
                    question.code            = q.get('code', '')
                    question.question_type   = q.get('type', 'likert')
                    question.hmsam_construct = q.get('construct', '') or None
                    question.order           = i
                    question.is_required     = q.get('required', True)
                    question.rating_style    = q.get('ratingStyle', 'stars')
                    question.rating_max      = int(q.get('ratingMax', 5))
                    question.section_title   = q.get('sectionTitle', '')
                    question.section_num     = int(q.get('sectionNum', 1))
                    question.save()
                else:
                    # NEW question — created fresh, old responses have no answer for it
                    question = Question.objects.create(
                        survey=survey,
                        text=q.get('text', ''),
                        code=q.get('code', ''),
                        question_type=q.get('type', 'likert'),
                        hmsam_construct=q.get('construct', '') or None,
                        order=i,
                        is_required=q.get('required', True),
                        rating_style=q.get('ratingStyle', 'stars'),
                        rating_max=int(q.get('ratingMax', 5)),
                        section_title=q.get('sectionTitle', ''),
                        section_num=int(q.get('sectionNum', 1)),
                    )

                kept_ids.append(question.id)

                # Update options IN PLACE so Answer.selected_option keeps pointing
                # at the same rows. Only delete options actually removed.
                incoming_opts = q.get('options', [])
                existing_opts = list(question.options.all().order_by('order'))

                for j, opt_text in enumerate(incoming_opts):
                    if j < len(existing_opts):
                        o = existing_opts[j]
                        o.text  = opt_text
                        o.order = j
                        o.save()
                    else:
                        MCQOption.objects.create(question=question, text=opt_text, order=j)

                # Remove only the surplus options the creator actually deleted
                for o in existing_opts[len(incoming_opts):]:
                    o.delete()

            # Delete ONLY questions the creator actually removed
            survey.questions.exclude(id__in=kept_ids).delete()

        if action == 'draft':
            return JsonResponse({'redirect': f'/surveys/{survey.access_uuid}/features/'})
        else:
            return JsonResponse({
                'status':        'published',
                'dashboard_url': f'/surveys/{survey.access_uuid}/dashboard/',
            })

    # GET — load existing survey data into builder
    questions_data = []
    for q in survey.questions.all().order_by('order'):
        questions_data.append({
            'id':           q.id,
            'text':         q.text,
            'code':         q.code,
            'type':         q.question_type,
            'construct':    q.hmsam_construct or '',
            'required':     q.is_required,
            'options':      [opt.text for opt in q.options.all()],
            'ratingMax':    q.rating_max,
            'ratingStyle':  q.rating_style,
            'sectionTitle': q.section_title,
            'sectionNum':   q.section_num,
        })

    return render(request, 'surveys/survey_builder.html', {
        'is_hmsam': survey.is_hmsam,
        'survey_type': 'hmsam' if survey.is_hmsam else 'standard',
        'hmsam_questions_json': '[]',
        'edit_mode': True,
        'edit_uuid': str(survey.access_uuid),
        'prefill_title': survey.title,
        'prefill_desc': survey.description,
        'prefill_questions': json.dumps(questions_data),
        'prefill_accent': survey.theme_accent,
        'prefill_bg': survey.theme_bg,
        'prefill_submit_label': survey.submit_label,
        'prefill_btn_color': survey.btn_color,
        'prefill_btn_radius': survey.btn_radius,
        'prefill_header_image': survey.header_image_b64,
        'prefill_q_font':       survey.q_font,       
        'prefill_header_font':  survey.header_font,
        'save_url':             f'/surveys/{survey.access_uuid}/edit/', #overrides the save URL so the builder posts to edit endpoint
    })

@login_required
@require_POST
def delete_survey(request, uid):
    survey = get_object_or_404(Survey, access_uuid=uid, organization=request.user)
    survey.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({'status': 'deleted'})
    return redirect('my_surveys')


@login_required
def ab_comparison(request):
    gamified = get_object_or_404(Survey, access_uuid=request.GET.get('a'), organization=request.user)
    plain    = get_object_or_404(Survey, access_uuid=request.GET.get('b'), organization=request.user)
    return render(request, 'surveys/ab_comparison.html', {
        'r': compare_surveys(gamified, plain),
    })