package org.sigurnisignal

import android.app.*
import android.content.Context
import android.content.Intent
import android.os.*
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import org.meshtastic.proto.MeshProtos
import org.meshtastic.proto.Portnums
import org.meshtastic.proto.TelemetryProtos

/** One runtime per process; no cloud/network scheduler. Explicit foreground service owns BLE. */
object Runtime {
    data class State(val link:String="Radio nije povezan",val connected:Boolean=false,val revision:Int=0,val error:String?=null,val radioBattery:String?=null)
    val state=MutableStateFlow(State())
    private var store:SecureStore?=null
    fun database(context:Context):SecureStore = synchronized(this){store?:SecureStore(context.applicationContext).also{store=it;it.recoverUncertain()}}
    fun changed(){state.update{it.copy(revision=it.revision+1)}}
}
class RadioService:Service() {
    private lateinit var radio:MeshtasticBle
    private lateinit var db:SecureStore
    private val handler=Handler(Looper.getMainLooper())
    private val secureRandom=java.security.SecureRandom()
    private val prefs by lazy{getSharedPreferences("settings",MODE_PRIVATE)}
    private val tick=object:Runnable {override fun run(){
        try {
            if(radio.ready && prefs.getBoolean("rf_reviewed",false)) {
                val packet=secureRandom.nextInt().let{if(it==0)1 else it}
                val blocked=db.list().firstOrNull{!it.incoming && it.state in listOf("queued","submitted") && radio.policyError(it.channel)!=null}
                if(blocked!=null)Runtime.state.update{it.copy(error=radio.policyError(blocked.channel))}
                val next=db.reserveNext(packet.toLong() and 0xffffffffL,System.currentTimeMillis()/1000){radio.policyError(it.channel)==null}
                if(next!=null) {
                    Runtime.changed()
                    radio.send(next,packet){ok-> db.submitted(next.id,ok);Runtime.changed() }
                }
            }
        }catch(e:Exception){Runtime.state.update{it.copy(error="Slanje zaustavljeno: ${e.message}")}}
        handler.postDelayed(this,5000)
    }}
    override fun onCreate(){
        super.onCreate();db=Runtime.database(this)
        val nm=getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel("radio","Radijska veza",NotificationManager.IMPORTANCE_LOW))
        nm.createNotificationChannel(NotificationChannel("received","Primljene poruke",NotificationManager.IMPORTANCE_DEFAULT))
        val open=PendingIntent.getActivity(this,0,Intent(this,MainActivity::class.java),PendingIntent.FLAG_IMMUTABLE)
        startForeground(1,NotificationCompat.Builder(this,"radio").setSmallIcon(android.R.drawable.stat_sys_data_bluetooth)
            .setContentTitle("Sigurni Signal").setContentText("Radijska veza aktivna; primitak ovisi o radioopremi.").setContentIntent(open).setOngoing(true).build())
        radio=MeshtasticBle(this,{text,ready->Runtime.state.update{it.copy(link=text,connected=ready)}},{frame->received(frame)})
        handler.post(tick)
    }
    override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int {
        intent?.getStringExtra("address")?.let{radio.connect(it)}
        return START_NOT_STICKY
    }
    private fun received(frame:MeshProtos.FromRadio) {
        if(!frame.hasPacket())return
        val p=frame.packet;if(!p.hasDecoded())return
        val d=p.decoded
        try {
            if(d.portnum==Portnums.PortNum.ROUTING_APP && d.requestId!=0) {
                val routing=MeshProtos.Routing.parseFrom(d.payload)
                db.radioAck(d.requestId.toLong() and 0xffffffffL,routing.errorReasonValue)
            } else if(d.portnum==Portnums.PortNum.TELEMETRY_APP && p.from==radio.localNodeNumber) {
                val telemetry=TelemetryProtos.Telemetry.parseFrom(d.payload)
                if(telemetry.hasDeviceMetrics()){
                    val level=telemetry.deviceMetrics.batteryLevel
                    val label=when(level){in 0..100->"$level %";101->"Vanjsko napajanje";else->"Nepoznata baterija radija"}
                    Runtime.state.update{it.copy(radioBattery=label)}
                }
            } else if(d.portnum==Portnums.PortNum.TEXT_MESSAGE_APP) {
                if(!d.payload.isValidUtf8 || d.payload.size()>233)return
                val sender="!"+java.lang.Integer.toUnsignedString(p.from,16).padStart(8,'0')
                db.receive(sender,p.id.toLong() and 0xffffffffL,d.payload.toStringUtf8(),p.channel)
                getSystemService(NotificationManager::class.java).notify(2,NotificationCompat.Builder(this,"received")
                    .setSmallIcon(android.R.drawable.stat_notify_chat).setContentTitle("Primljena radijska poruka")
                    .setContentText("Otvorite aplikaciju; sadržaj i pošiljalac nisu službeno provereni.").setAutoCancel(true).build())
            }
            Runtime.changed()
        }catch(_:Exception){Runtime.state.update{it.copy(error="Neispravan ili nepodržan paket odbačen")}}
    }
    override fun onDestroy(){handler.removeCallbacksAndMessages(null);radio.close();Runtime.state.update{it.copy(link="Radio odspojen",connected=false)};super.onDestroy()}
    override fun onBind(intent:Intent?)=null
}
