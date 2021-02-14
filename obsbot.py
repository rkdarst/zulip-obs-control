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
    # 'OBS microphone source name'
    'A_Desktop Audio',
    }

# Mapping between scene names and OBS names.  Edit to suit you.
SCENES = {
    # 'ID': 'OBS scene name'
    'blank': 'Empty',
    'title': 'Title card',
    'gallery': 'Gallery',
    'screen': 'Desktop (remote)+camera',
    }

TEXTS = {
    # 'ID': ['obs_source_name', ...],
    'front': [
        'Timing text'
             ]
    }


#### End user configuration

# https://github.com/Elektordi/obs-websocket-py/tree/master/obswebsocket
ws = obsws(host, port, password)



### Initial connection: verify websocket and verify that the scenes, microphones, and other things above are correct.

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


# Dispatchers is a mapping that directs commands to functions, based on
# compiled regex objects.
DISPATCHERS = {
    # compiled_regex: function_to_call,
    }
def dispatcher(regex, regex_options=re.I|re.M):
    """Decorator to add a function to DISPATCHERS"""
    if isinstance(regex, str):
        regex = re.compile(regex, regex_options)
    def _(f):
        DISPATCHERS[regex] = f
        return f
    return _




#### The different handlers

@dispatcher(re.compile(r'^(?:switch)\s*(.*)', re.I|re.M))
def switch(bh, msg, scene):
    """Switch OBS scenes"""
    print(scene)
    # Help text
    help = '\n'.join(['available scenes: '+ ' '.join(
                                 '`'+x+'`' for x in sorted(SCENES.keys())),
            'switch with `switch $NAME`',
            ])
    if not scene or scene not in SCENES:
        return help

    ws.connect()
    # Set the scene
    ws.call(requests.SetCurrentScene(SCENES[scene]))
    # Get current scene and verify it is as expected
    ret = ws.call(requests.GetCurrentScene())
    ws.disconnect()
    # React if it works
    if ret.getName() == SCENES[scene]:
        bh.react(msg, 'check_mark')

# Create shortcut scene switchers
for scenename in SCENES.keys():
    @dispatcher('^%s\s*'%scenename)
    def switch_to(bh, msg, scenename=scenename):
        return switch(bh, msg, scenename)



@dispatcher('^help\s*')
def help_(bh, msg):
    """Print help text"""
    scenes = ', '.join('`%s`'%x for x in SCENES.keys())
    texts = ', '.join('`%s`'%x for x in TEXTS.keys())
    lines = [
        "* 'switch [scene-name]` or just `[scene-name]`: switch scene",
        "* 'text [text-item] [content]` or just `[text-item] [content]`: adjust text content",
        "* `mute`, `unmute` (only Zoom audio, not broadcaster's microphone)",
        "* scenes: %s"%scenes,
        "* text-items: %s"%texts,
        "* `help`",
        ]
    return '\n'.join(lines)



@dispatcher(r'^mute\s*')
def mute(bh, msg, mute=True):
    ws.connect()
    # Request everything be muted
    for mic in MICROPHONES:
        ws.call(requests.SetMute(mic, mute=mute))
    # Go through again, verify that all the muting worked
    mute_status = []
    for mic in MICROPHONES:
        ret = ws.call(requests.GetMute(mic))
        print(ret)
        mute_status.append(ret.getMuted())
    ws.disconnect()
    # React based on if everything was muted or not.  React based on current
    # status (currently muted or not), not based on if it was successful or
    # not.
    if all(mute_status):
        bh.react(msg, 'mute_notifications')
    elif not any(mute_status):
        bh.react(msg, 'notifications')
    else:
        return "Mute statuses: %s"%' '.join(str(x) for x in mute_status)

@dispatcher(r'^unmute\s*')
def unmute(bh, msg, mute=False):
    """Unmute"""
    return globals()['mute'](bh, msg, mute=False)


@dispatcher(r'^react\s*')
def react(bh, msg, mute=False):
    """Create a test reaction"""
    bh.react(msg, 'check_mark')


@dispatcher(r'^text\s+(\S+)\s+(.*)', re.I|re.M|re.DOTALL)
def text(bh, msg, textname, content):
    """Update the content of a text field.

    Since we may want to keep several in sync, update over a loop.
    """
    ws.connect()
    updated_status = [ ]
    content = content.strip()
    content = content.replace('\\n', '\n')
    # Loop over the different text fields
    for textid in TEXTS[textname]:
        ret = ws.call(requests.SetTextFreetype2Properties(textid, text=content))
        ret = ws.call(requests.GetTextFreetype2Properties(textid))
        updated_status.append(ret.getText() == content)
    ws.disconnect()
    # Check that everything was successfully updated
    if all(updated_status):
        bh.react(msg, 'check_mark')


for text_item in TEXTS.keys():
    @dispatcher('^%s\s+(.*)'%text_item)
    def update_text(bh, msg, content, text_item=text_item):
        return text(bh, msg, text_item, content)



@dispatcher(r'^raise_exception\s*')
def raise_exception(bh, msg, mute=False):
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
            def dummy_react(msg, react):
                print("REACT:", react)
            bot_handler.react = dummy_react

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
