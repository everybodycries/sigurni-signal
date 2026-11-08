"""Official SDK USB adapter; no TCP/cloud transport and no HF control.
SPDX-License-Identifier: GPL-3.0-only
"""
import threading
import time

def profile_check(interface):
    """Check the read-only candidate profile; never mutate the radio."""
    config=interface.localNode.localConfig.lora
    if int(config.region)!=3 or config.override_duty_cycle:
        return False,'Slanje blokirano: potreban provjeren EU_868 profil bez override_duty_cycle.'
    channels=interface.localNode.channels
    channel=next((c for c in channels if c.index==0),None)
    if channel is None or int(channel.role)!=1:
        return False,'Slanje blokirano: primarni kanal0 nije dostupan.'
    settings=channel.settings; psk=bytes(settings.psk)
    public=bytes.fromhex('d4f1bb3a20290759f0bcffabcf4e6901')
    known={public[:-1]+bytes([public[-1]+i]) for i in range(10)}
    if len(psk) not in (16,32) or not any(psk) or psk in known:
        return False,'Slanje blokirano: potreban je privatni ključ kanala, bez javnog zadanog ključa.'
    if settings.uplink_enabled or settings.downlink_enabled or interface.localNode.moduleConfig.mqtt.enabled:
        return False,'Slanje blokirano: isključite MQTT i internetski uplink/downlink u službenom klijentu.'
    return True,''

class RadioWorker:
    def __init__(self,store,port=None):
        self.store=store; self.port=port; self.interface=None
        self.stop_event=threading.Event(); self.thread=None; self.last_error=''
        self.last_received_at=None; self.last_connected_at=None
        self.config_safe=False; self.region=None; self._early_acks={}; self._ack_lock=threading.RLock()
    def status(self):
        connected=bool(self.interface and self.interface.isConnected.is_set())
        return {'configured_port':self.port or '', 'connected':connected,
                'enabled':self.store.settings()['radio_enabled'], 'profile_safe':self.config_safe,
                'region':self.region,'last_error':self.last_error,'last_received_at':self.last_received_at,
                'last_connected_at':self.last_connected_at,
                'notice':'USB/BLE ili radijska potvrda ne potvrđuje primitak osobe. Nema HF automatike.'}
    def start(self):
        if self.thread: return
        self.thread=threading.Thread(target=self._run,name='meshtastic-usb',daemon=True); self.thread.start()
    def stop(self):
        self.stop_event.set()
        if self.interface:
            try: self.interface.close()
            except Exception: pass
        if self.thread: self.thread.join(timeout=3)
    def _on_packet(self,packet,interface=None):
        if interface is not self.interface: return
        try:
            decoded=packet.get('decoded',{}); now=int(time.time())
            if decoded.get('portnum')=='TEXT_MESSAGE_APP' and 'text' in decoded:
                sender=packet.get('fromId') or ('!%08x'%packet.get('from',0))
                self.store.receive(decoded['text'],sender,packet['id'],now=now)
                self.last_received_at=now
            if decoded.get('portnum')=='ROUTING_APP' and decoded.get('requestId'):
                routing=decoded.get('routing',{}); error=routing.get('errorReason','NONE')
                # Routing ACK remains an unverified radio-layer report, never a human receipt.
                packet_id=int(decoded['requestId'])
                with self._ack_lock:
                    self._early_acks[packet_id]=(error,now)
                    self._early_acks={k:v for k,v in self._early_acks.items() if now-v[1]<120}
                    self.store.radio_ack(packet_id,error,now=now)
        except (ValueError,KeyError,TypeError):
            self.last_error='Odbačen neispravan ili nepodržan dolazni paket.'
    def _connect(self):
        if not self.port: return
        from meshtastic.serial_interface import SerialInterface
        from pubsub import pub
        pub.subscribe(self._on_packet,'meshtastic.receive')
        try:
            self.interface=SerialInterface(devPath=self.port,timeout=10)
            config=self.interface.localNode.localConfig.lora
            self.region=int(config.region)
            self.config_safe,self.last_error=profile_check(self.interface)
            self.last_connected_at=int(time.time())
        except Exception:
            pub.unsubscribe(self._on_packet,'meshtastic.receive'); raise
    def _run(self):
        # No auto-discovery: only an explicitly supplied serial path is opened.
        if not self.port: return
        try:
            self._connect()
            while not self.stop_event.wait(1):
                if not self.store.settings()['radio_enabled']: continue
                self.config_safe,profile_error=profile_check(self.interface)
                if not self.config_safe:
                    self.last_error=profile_error
                    continue
                if not self.interface or not self.interface.isConnected.is_set():
                    self.last_error='USB veza je prekinuta; red je zaustavljen. Ponovno pokrenite konzolu nakon provjere.'
                    continue
                job=self.store.reserve_next()
                if not job: continue
                try:
                    destination='^all' if job['destination']=='all' else job['destination']
                    packet=self.interface.sendText(job['wire'],destinationId=destination,
                             wantAck=destination!='^all',channelIndex=0)
                    if packet is None or not packet.id: raise RuntimeError('SDK nije vratio oznaku paketa.')
                    with self._ack_lock:
                        self.store.mark_submitted(job['id'],packet.id)
                        ack=self._early_acks.pop(packet.id,None)
                        if ack: self.store.radio_ack(packet.id,ack[0],now=ack[1])
                except Exception as exc:
                    self.last_error=f'Neizvjesna predaja radiju ({type(exc).__name__}); potreban pregled.'
                    self.store.mark_uncertain(job['id'],self.last_error)
        except ImportError:
            self.last_error='Meshtastic SDK nije instaliran. Instalirajte requirements-radio.txt u virtualno okruženje.'
        except Exception as exc:
            self.last_error=f'USB povezivanje nije uspjelo ({type(exc).__name__}). Nije potvrđeno slanje.'
        finally:
            try:
                from pubsub import pub
                pub.unsubscribe(self._on_packet,'meshtastic.receive')
            except ImportError: pass
