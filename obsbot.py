import re
import subprocess
import traceback

from zulip_bots.terminal import TerminalBotHandler

from obswebsocket import obsws, requests  # noqa: E402

host = "localhost"
port = 4444
password = "secret"

# Email addresses of users who will be allowed to command the bot.  (Emails are
# the unique IDs of users)
AUTHORIZED_USERS = {
    'user126348@zulipchat.com',
    }

# Microphones which will be muted/unmuted when `mute` is given.
MICROPHONES = {
    'A_Desktop Audio',
    }

# Mapping between scene names and OBS names.  Edit to suit you.
SCENES = {
    'blank': 'Empty',
    'title': 'Title card',
    'gallery': 'Gallery',
    'screen': 'Desktop (remote)+camera',
    }


#### End user configuration

# https://github.com/Elektordi/obs-websocket-py/tree/master/obswebsocket
ws = obsws(host, port, password)



### Initial connection: verify websocket and scenes are correct
ws.connect()
# Test the OBS scenes (video)
ret = ws.call(requests.GetSceneList())
obs_scenes = { x['name'] for x in ret.getScenes() }
print('OBS found scenes:', obs_scenes)
for scene_id in SCENES.values():
    if scene_id not in obs_scenes:
        raise RuntimeError("Scene '%s' not found"%scene_id)
# Test the OBS sources (audio)
ret = ws.call(requests.GetSourcesList())
obs_sources = { x['name'] for x in ret.getSources() }
print('OBS found sources:', obs_sources)
for mic in MICROPHONES:
    if mic not in obs_sources:
        raise RuntimeError("Source '%s' not found"%mic)
ws.disconnect()


DISPATCHERS = {
    }
def dispatcher(regex):
    if isinstance(regex, str):
        regex = re.compile(regex, re.I|re.M)
    def _(f):
        DISPATCHERS[regex] = f
        return f
    return _




#### The different handlers

@dispatcher(re.compile(r'^(?:switch)\s*(.*)', re.I|re.M))
def switch(bh, msg, scene):
    print(scene)
    help = '\n'.join(['available scenes: '+ ' '.join(
                                 '`'+x+'`' for x in sorted(SCENES.keys())),
            'switch with `switch $NAME`',
            ])
    if not scene or scene not in SCENES:
        return help

    ws.connect()
    ws.call(requests.SetCurrentScene(SCENES[scene]))
    ret = ws.call(requests.GetCurrentScene())
    ws.disconnect()
    if ret.getName() == SCENES[scene]:
        bh.react(msg, 'check_mark')

for scenename in SCENES.keys():
    @dispatcher('^%s\s*'%scenename)
    def switch_to(bh, msg, scenename=scenename):
        return switch(bh, msg, scenename)



@dispatcher('^help\s*')
def help_(bh, msg):
    lines = [
        "* scene switching: `title`, `gallery`, `screen`, `blank`",
        "* `mute`, `unmute` (only Zoom audio, not broadcaster's microphone)",
        "* `help`",
        ]
    return '\n'.join(lines)



@dispatcher(r'^mute\s*')
def mute(bh, msg, mute=True):
    ws.connect()
    for mic in MICROPHONES:
        ws.call(requests.SetMute(mic, mute=mute))
    mute_status = []
    for mic in MICROPHONES:
        ret = ws.call(requests.GetMute(mic))
        print(ret)
        mute_status.append(ret.getMuted())
    ws.disconnect()
    if all(mute_status):
        bh.react(msg, 'mute_notifications')
    elif not any(mute_status):
        bh.react(msg, 'notifications')
    else:
        return "Mute statuses: %s"%' '.join(str(x) for x in mute_status)

@dispatcher(r'^unmute\s*')
def unmute(bh, msg, mute=False):
    return globals()['mute'](bh, msg, mute=False)


@dispatcher(r'^react\s*')
def react(bh, msg, mute=False):
    bh.react(msg, 'check_mark')

@dispatcher(r'^raise_exception\s*')
def react(bh, msg, mute=False):
    raise RuntimeError("Raising requested exception")



class MyBotHandler(object):
    '''
    A docstring documenting this bot.
    '''

    def usage(self):
        return '''Your description of the bot'''

    def handle_message(self, message, bot_handler):
        # add your code here
        #print('self', self)
        print('message', message)
        #print('bot_handler', bot_handler)

        # Terminal-based version doesn't do reactions
        if isinstance(bot_handler, TerminalBotHandler):
            bot_handler.react = lambda msg, react: None

        try:
            # Test sender email for authorization to send
            if message['sender_email'] not in AUTHORIZED_USERS \
              and not (message['sender_email']=='foo_sender@zulip.com' and 'id' not in message):
                return

            type = message.get('type')
            content = message['content']
            stream = ''
            for re, function in DISPATCHERS.items():
                m = re.search(content)
                if m:
                    print('running', function, m.groups())
                    try:
                        response = function(bot_handler, message, *m.groups())
                        if response:
                            bot_handler.send_reply(message, response)
                    except:
                        traceback.print_exc()
                        bot_handler.react(message, 'boom')

        except:
            traceback.print_exc()

        return

handler_class = MyBotHandler
