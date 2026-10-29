# Levels — (min_points, level_num, title, max_points)
LEVELS = [
    (0,    1, 'New Voice',          99),
    (100,  2, 'Contributor',        299),
    (300,  3, 'Active Member',      599),
    (600,  4, 'Trusted Respondent', 999),
    (1000, 5, 'Community Champion', None),
]

# Badges — (key, name, image placeholder, points threshold)
BADGES = [
    ('new_voice',  'New Voice',          'badge_new_voice.png',  0),
    ('contributor','Contributor',        'badge_contributor.png',100),
    ('active',     'Active Member',       'badge_active.png',     300),
    ('trusted',    'Trusted Respondent',  'badge_trusted.png',    600),
    ('champion',   'Community Champion',  'badge_champion.png',   1000),
]

def get_level_info(total_points):
    for min_pts, level, title, max_pts in LEVELS:
        if max_pts is None or total_points <= max_pts:
            if max_pts:
                span     = max_pts - min_pts + 1
                progress = int(((total_points - min_pts) / span) * 100)
                needed   = max_pts + 1 - total_points
                nxt      = LEVELS[level][2]
            else:
                progress, needed, nxt = 100, 0, None
            return {
                'level': level, 'title': title, 'points': total_points,
                'progress': max(0, min(100, progress)),
                'next_title': nxt, 'points_needed': needed,
            }
    return {'level': 1, 'title': 'New Voice', 'points': total_points,
            'progress': 0, 'next_title': 'Contributor', 'points_needed': 100}

def get_badges(total_points):
    """Returns earned badge (highest reached) and the next locked badge."""
    earned = None
    nxt    = None
    for key, name, image, threshold in BADGES:
        if total_points >= threshold:
            earned = {'key': key, 'name': name, 'image': image, 'threshold': threshold}
        elif nxt is None:
            nxt = {'key': key, 'name': name, 'image': image,
                   'threshold': threshold, 'away': threshold - total_points}
    return earned, nxt

def get_badges(total_points):
    earned = None
    nxt    = None
    prev_threshold = 0
    for key, name, image, threshold in BADGES:
        if total_points >= threshold:
            earned = {'key': key, 'name': name, 'image': image, 'threshold': threshold}
            prev_threshold = threshold
        elif nxt is None:
            span     = threshold - prev_threshold
            progress = int(((total_points - prev_threshold) / span) * 100) if span else 0
            nxt = {
                'key': key, 'name': name, 'image': image,
                'threshold': threshold,
                'away': threshold - total_points,
                'progress': max(0, min(100, progress)),
            }
    return earned, nxt