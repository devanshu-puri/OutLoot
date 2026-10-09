import urllib.request
import json
import time

base_url = 'http://127.0.0.1:8000'

def request(path, method='GET', data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    encoded_data = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f'{base_url}{path}', data=encoded_data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def run_tests():
    print('=== 1. TEST ANON AUTH ===')
    auth = request('/api/auth/anon', method='POST')
    token = auth['token']
    user_id = auth['user_id']
    print(f'Authenticated anon user: {user_id}')

    print('\n=== 2. TEST INITIAL SCREEN TIME & WELLBEING SUMMARY ===')
    summary = request('/api/screentime/summary', token=token)
    print(f'Initial Summary: streak={summary["screen_streak_minutes"]}m, ratio={summary["grass_ratio"]}')
    assert summary['screen_streak_minutes'] == 0.0

    print('\n=== 3. TEST ACTIVE SCREEN TIME HEARTBEAT (15 mins) ===')
    hb1 = request('/api/screentime/heartbeat', method='POST', data={'active_s': 900.0, 'idle_s': 0.0}, token=token)
    print(f'Heartbeat 1: streak={hb1["current_screen_streak_s"]}s, alert={hb1["touch_grass_alert"]}')

    print('\n=== 4. TEST UPDATE THRESHOLD TO 15 MINS ===')
    thresh_res = request('/api/screentime/threshold', method='POST', data={'threshold_minutes': 15}, token=token)
    print(f'Updated threshold: {thresh_res["threshold_minutes"]} mins')

    print('\n=== 5. TEST TRIGGER TOUCH GRASS ALERT ===')
    hb2 = request('/api/screentime/heartbeat', method='POST', data={'active_s': 60.0, 'idle_s': 0.0}, token=token)
    print(f'Heartbeat 2 alert={hb2["touch_grass_alert"]}, message: {hb2["message"]}')
    assert hb2['touch_grass_alert'] is True, 'Expected Touch Grass Alert to trigger!'

    print('\n=== 6. TEST ANDROID DIGITAL WELLBEING IMPORT ===')
    dw_res = request('/api/screentime/import', method='POST', data={'daily_screen_hours': 4.0, 'device_label': 'Pixel 8 Digital Wellbeing'}, token=token)
    print(f'Digital Wellbeing Import: {dw_res["message"]}')
    print(f'Suggested walk minutes: {dw_res["suggested_walk_mins"]} mins')
    assert dw_res['suggested_walk_mins'] >= 15

    print('\n=== 7. TEST LIVE LEADERBOARD ===')
    lb = request('/api/leaderboard', token=token)
    print(f'Total leaderboard walkers: {lb["total_walkers"]}, Current user rank: #{lb["user_rank"]}')
    for entry in lb['leaderboard'][:5]:
        print(f'  #{entry["rank"]} {entry["avatar_emoji"]} {entry["display_name"]}: {entry["points"]} pts, {entry["outdoor_mins"]}m walk, {entry["ratio_percent"]}% grass ratio')

    print('\n=== 8. TEST ADD FRIEND & SQUAD ROSTER ===')
    friend = request('/api/friends/add', method='POST', data={'friend_code_or_name': 'Alex Green'}, token=token)
    print(f'Added Friend: {friend["display_name"]} ({friend["avatar_emoji"]}) - {friend["status_msg"]}')

    friends_list = request('/api/friends', token=token)
    print(f'Friends Squad count: {len(friends_list)}')
    assert len(friends_list) >= 1

    print('\n=== 9. TEST FRIEND NUDGE ===')
    nudge_res = request('/api/friends/nudge', method='POST', data={'friend_id': friend['user_id'], 'message': '🌿 Step away from the IDE and touch grass!'}, token=token)
    print(f'Nudge sent status: {nudge_res["status"]}, ID: {nudge_res["nudge_id"]}')

    print('\n=== 10. TEST WALK SESSION & CYCLE PROGRESSION ===')
    session = request('/api/session/start', method='POST', data={'display_name': 'Dev Explorer', 'start_lat': 13.0827, 'start_lon': 80.2707}, token=token)
    sid = session['id']
    print(f'Started session: {sid}, State: {session["state"]}')

    t_now = time.time()
    samples = [
        {'t': t_now, 'lat': 13.0827, 'lon': 80.2707, 'accuracy_m': 4.0},
        {'t': t_now + 10, 'lat': 13.0828, 'lon': 80.2708, 'accuracy_m': 4.0},
        {'t': t_now + 20, 'lat': 13.0830, 'lon': 80.2710, 'accuracy_m': 4.0},
        {'t': t_now + 30, 'lat': 13.0832, 'lon': 80.2712, 'accuracy_m': 4.0},
        {'t': t_now + 40, 'lat': 13.0834, 'lon': 80.2714, 'accuracy_m': 4.0},
        {'t': t_now + 50, 'lat': 13.0836, 'lon': 80.2716, 'accuracy_m': 4.0},
    ]
    samples_res = request(f'/api/session/{sid}/samples', method='POST', data={'samples': samples}, token=token)
    print(f'Samples batch result: Distance: {samples_res["distance_m"]}m, Item Available: {samples_res["item_available"]}')

    print('\n=== 11. TEST REWARDS MARKETPLACE ===')
    rewards = request('/api/rewards')
    print(f'Total sponsor rewards: {len(rewards)}')
    for r in rewards[:3]:
        print(f'  🎁 {r["title"]} ({r["cost_points"]} pts) - {r["terms"]}')

    print('\n✨ ALL MVP 2.0 INTEGRATION FLOWS VERIFIED SUCCESSFULLY!')

if __name__ == '__main__':
    run_tests()
