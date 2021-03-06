# ClapToLightUp
# Created at 2020-05-25 14:43:55.054532

import streams
import checkDoubleClap as cdc
import buzzerFeedback as bfb
import switcher as swc
import light_driver as ld
import config as cfg
import timers
import internet

# Apertura stream seriale
streams.serial()

# Imposto il sensore di suono per la lettura analogica
sndSnsrPin = A0
pinMode(sndSnsrPin, INPUT_ANALOG)

# Imposto il led principale per la scrittura digitale
mainLedPin = D15
pinMode(mainLedPin, OUTPUT)

# Imposto i led di stato
enabledLedPin = D19
pinMode(enabledLedPin, OUTPUT)
mutedLedPin = D5
pinMode(mutedLedPin, OUTPUT)

# Imposto il button integrato per il cambio di modalità
modeButtonPin = BTN0
pinMode(modeButtonPin, INPUT_PULLUP)

# Inizializzo un ModeHandler
modeHandler = cfg.ModeHandler(enabledLedPin, mutedLedPin)

# Imposto il buzzer per funzionare in pwm
buzzerPin = D13.PWM
pinMode(buzzerPin, OUTPUT)

# Inizializzo il buzzer
buzzer = bfb.Buzzer(buzzerPin, modeHandler)

# Imposto il button per l'accensione manuale del led
lightButtonPin = D14
pinMode(lightButtonPin,INPUT_PULLDOWN)

# Imposto il button per la canzone
musicButtonPin = D27
pinMode(musicButtonPin, INPUT_PULLDOWN)

# Imposto un potenziometro per la regolazione della sensibilità del sistema
potentiometerPin = A4
pinMode(potentiometerPin,INPUT_ANALOG)

# Inizializzo un Listener
listener = cdc.Listener(sndSnsrPin, potentiometerPin)

# Inizializzo uno Switcher
switcher = swc.Switcher(mainLedPin, buzzer)

# Mi collego al wifi
internet.connect()


# Inizializzo il lightSensor
lightSensor = ld.LightSensor(I2C0)


def measureLight():
    brighnessPercentage = lightSensor.measure_high_res()
    publish_light(brighnessPercentage)

def publish_dnd():
    if client.connected():
        message = str(modeHandler.dnd)
        try:
            client.publish("current/dnd", message, qos=1, retain=True)
            print("Published dnd state:", message)
        except Exception as e:
            print('publish_light failed for message: ', message, e)
    

def publish_light(brighnessPercentage):
    if client.connected():
        message = str(brighnessPercentage)
        try:
            client.publish("current/light", message)
            print("Published detected light:", message)
        except Exception as e:
            print('publish_light failed for message: ', message, e)

def publish_leds_state():
    if client.connected():
        message = ""
        message += ('1 ' if switcher.ledState else '0 ') 
        message += ('1 ' if modeHandler.en    else '0 ')
        message += ('1'  if modeHandler.muted else '0' )
            
        try:
            client.publish("current/leds", message, retain=True)
            print("Published Led State:", message)
        except Exception as e:
            print('publish_leds_state failed for message: ', message, e)
    
    
# define MQTT callbacks
def on_luce_message(mqtt_client, payload, topic):
    switcher.set(payload)
    
def on_mode_message(mqtt_client, payload, topic):
    modeHandler.set(payload)
    
def on_change_message(mqtt_client, payload, topic):
    modeHandler.changeMode()
    
def on_DND_message(mqtt_client, payload, topic):
    modeHandler.setDND(payload)
    publish_dnd()
    

modeHandler.on_change(publish_leds_state)
switcher.on_change(publish_leds_state)

# Alla pressione del bottone integrato cambio la modalità
onPinFall(modeButtonPin, modeHandler.changeMode)

# Alla pressione del bottone della luce cambio lo stato del led principale
onPinFall(lightButtonPin, switcher.switch, "From Button")

# Alla pressione del bottone della musica avvio o stoppo la riproduzione
onPinFall(musicButtonPin, bfb.startStop, buzzer)


# Inizializzo il timer per le misurazioni del lightSensor
t = timers.timer()
t.interval(1500, measureLight)

# Inizializzo il client MQTT
client = internet.Client("zerynth-mqtt-marco741")
    
# subscribe to channels
def aconnect_cb():
    print("connected.")
    global client
    client.subscribe("new/luce", on_luce_message, 1)
    client.subscribe("new/mode", on_mode_message, 1)
    client.subscribe("new/change", on_change_message, 1)
    client.subscribe("new/dnd", on_DND_message, 1)
    client.publish("current/connected", "True", qos=1, retain=True)
    publish_leds_state()

try:
    client.connect("test.mosquitto.org", aconnect_cb=aconnect_cb)
    
    print("Starting loop")
    while(True):
        # Se il Listener rileva un segnale di commutazione, commuto lo stato del led tramite lo switcher
        if modeHandler.en and listener.listen():
            switcher.switch("From Sound")
            
        sleep(cfg.SCAN_PERIOD)
except Exception as e:
    print(e)