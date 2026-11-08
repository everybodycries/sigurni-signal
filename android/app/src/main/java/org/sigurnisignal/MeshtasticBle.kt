package org.sigurnisignal

import android.annotation.SuppressLint
import android.bluetooth.*
import android.bluetooth.le.*
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.os.ParcelUuid
import com.google.protobuf.ByteString
import org.meshtastic.proto.MeshProtos
import org.meshtastic.proto.Portnums
import org.meshtastic.proto.ChannelProtos
import org.meshtastic.proto.ConfigProtos
import java.util.UUID

/** Uses official pinned protobufs and official GATT UUIDs; never programs RF/channel settings. */
@SuppressLint("MissingPermission")
class MeshtasticBle(private val context:Context,private val onState:(String,Boolean)->Unit,private val onPacket:(MeshProtos.FromRadio)->Unit) {
    companion object {
        val SERVICE:UUID=UUID.fromString("6ba1b218-15a8-461f-9fa8-5dcae273eafd")
        val TO:UUID=UUID.fromString("f75c76d2-129e-4dad-a1dd-7866124401e7")
        val FROM:UUID=UUID.fromString("2c55e69e-4993-11ed-b878-0242ac120002")
        val NUM:UUID=UUID.fromString("ed9da18c-a800-4f66-a670-aa7547e34453")
        val CCC:UUID=UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")
    }
    private val handler=Handler(Looper.getMainLooper())
    private val adapter=(context.getSystemService(Context.BLUETOOTH_SERVICE)as BluetoothManager).adapter
    private var gatt:BluetoothGatt?=null
    private var to:BluetoothGattCharacteristic?=null
    private var from:BluetoothGattCharacteristic?=null
    private val operations=ArrayDeque<()->Boolean>()
    private var busy=false
    private val drain=ReadDrain()
    private var token=0
    private var myNode=0
    private var negotiatedMtu=23
    private var lora:ConfigProtos.Config.LoRaConfig?=null
    private var mqttEnabled:Boolean?=null
    private val channels=mutableMapOf<Int,ChannelProtos.Channel>()
    private var closed=false
    private var writeResult:((Boolean)->Unit)?=null
    val localNodeNumber:Int get()=myNode
    var ready=false;private set
    private val timeout=Runnable { fail("Bluetooth postupak je istekao. Provjerite radio i ponovno povežite.") }
    private fun enqueue(action:()->Boolean) { operations.addLast(action); pump() }
    private fun pump() {
        if(busy || operations.isEmpty() || closed)return
        busy=true;handler.postDelayed(timeout,15000)
        try { if(!operations.removeFirst().invoke())fail("Radio nije prihvatio Bluetooth postupak") }
        catch(_:SecurityException){ fail("Nedostaje Bluetooth dopuštenje") }
        catch(_:Exception){ fail("Bluetooth veza nije dostupna") }
    }
    private fun done(status:Int) {
        handler.removeCallbacks(timeout);busy=false
        if(status!=BluetoothGatt.GATT_SUCCESS){fail("Bluetooth pogreška $status; isporuka nepoznata");return}
        pump()
    }
    private fun fail(message:String) { close();onState(message,false) }
    fun connect(address:String) {
        close();closed=false;onState("Povezivanje s radiouređajem…",false)
        try {gatt=adapter.getRemoteDevice(address).connectGatt(context,false,callback,BluetoothDevice.TRANSPORT_LE)}
        catch(_:Exception){fail("Povezivanje nije uspjelo. Provjerite dopuštenja i Bluetooth.")}
    }
    fun close() {
        closed=true;ready=false;handler.removeCallbacks(timeout);operations.clear();busy=false;drain.reset()
        writeResult?.invoke(false);writeResult=null
        gatt?.disconnect();gatt?.close();gatt=null;to=null;from=null;myNode=0;lora=null;mqttEnabled=null;channels.clear();negotiatedMtu=23
    }
    fun policyError(channel:Int):String? {
        val cfg=lora ?:return "Radio nije dostavio LoRa postavke; slanje je zaključano"
        if(cfg.region.name!="EU_868")return "Pilot prihvaća samo prethodno odobreni EU_868 profil; provjerite lokalnu dopuštenost"
        if(cfg.overrideDutyCycle)return "Radio ima uključen override duty-cycle; slanje je zaključano"
        if(mqttEnabled==null)return "Radio nije dostavio MQTT postavke; slanje je zaključano"
        if(mqttEnabled==true)return "MQTT modul mora biti isključen za ovaj offline pilot"
        val c=channels[channel] ?:return "Odabrani kanal nije dostavljen; slanje je zaključano"
        if(c.roleValue==0 || !c.hasSettings())return "Odabrani kanal nije aktivan"
        val key=c.settings.psk.toByteArray()
        if(key.size !in listOf(16,32) || key.all{it==0.toByte()})return "Potrebno je postaviti osobno podijeljen privatni ključ kanala"
        val publicKey=byteArrayOf(0xd4.toByte(),0xf1.toByte(),0xbb.toByte(),0x3a,0x20,0x29,0x07,0x59,0xf0.toByte(),0xbc.toByte(),0xff.toByte(),0xab.toByte(),0xcf.toByte(),0x4e,0x69,0x01)
        if(key.size==16 && key.take(15)==publicKey.take(15) && ((key[15].toInt()and 255) in 1..10))return "Javni zadani ključ nije prihvatljiv za privatnu komunikaciju"
        if(c.settings.uplinkEnabled || c.settings.downlinkEnabled)return "MQTT uplink/downlink kanala mora biti isključen za ovaj pilot"
        return null
    }
    fun send(message:Message,packetId:Int,result:(Boolean)->Unit) {
        if(!ready || writeResult!=null || policyError(message.channel)!=null){result(false);return}
        val text=Protocol.encode(message.id,message.body)
        val data=MeshProtos.Data.newBuilder().setPortnum(Portnums.PortNum.TEXT_MESSAGE_APP).setPayload(ByteString.copyFromUtf8(text)).build()
        val destination=if(message.destination=="^all")-1 else message.destination.removePrefix("!").toLong(16).toInt()
        val packet=MeshProtos.MeshPacket.newBuilder().setFrom(myNode).setTo(destination).setId(packetId).setChannel(message.channel)
            .setWantAck(destination != -1).setDecoded(data).setHopLimit(3).build()
        writeResult=result
        enqueue {write(MeshProtos.ToRadio.newBuilder().setPacket(packet).build().toByteArray())}
    }
    private fun write(bytes:ByteArray):Boolean {
        val characteristic=to ?:return false
        if(bytes.size>negotiatedMtu-3)return false
        characteristic.writeType=BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
        characteristic.value=bytes
        return gatt?.writeCharacteristic(characteristic)==true
    }
    private fun readNext() {
        if(closed || !drain.request())return
        enqueue { gatt?.readCharacteristic(from)==true }
    }
    private val callback=object:BluetoothGattCallback() {
        override fun onConnectionStateChange(g:BluetoothGatt,status:Int,newState:Int) {handler.post {
            if(g!==gatt)return@post
            if(status!=0 || newState==BluetoothProfile.STATE_DISCONNECTED){fail("Radio odspojen. Nepotvrđene poruke ostaju spremljene.");return@post}
            if(newState==BluetoothProfile.STATE_CONNECTED)enqueue {g.requestMtu(512)}
        }}
        override fun onMtuChanged(g:BluetoothGatt,mtu:Int,status:Int) {handler.post {
            if(g!==gatt)return@post
            if(status!=0 || mtu<240){fail("Radio ne podržava potreban BLE MTU");return@post}
            negotiatedMtu=mtu;enqueue{g.discoverServices()};done(status)
        }}
        override fun onServicesDiscovered(g:BluetoothGatt,status:Int){handler.post {
            if(g!==gatt)return@post
            val service=g.getService(SERVICE)
            to=service?.getCharacteristic(TO);from=service?.getCharacteristic(FROM)
            val num=service?.getCharacteristic(NUM);val ccc=num?.getDescriptor(CCC)
            if(status!=0 || to==null || from==null || num==null || ccc==null){fail("Uređaj nema Meshtastic BLE servis");return@post}
            g.setCharacteristicNotification(num,true);ccc.value=BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
            enqueue{g.writeDescriptor(ccc)};done(status)
        }}
        override fun onDescriptorWrite(g:BluetoothGatt,d:BluetoothGattDescriptor,status:Int){handler.post {
            if(g!==gatt)return@post
            token=java.security.SecureRandom().nextInt().let{if(it==0)1 else it}
            enqueue {write(MeshProtos.ToRadio.newBuilder().setWantConfigId(token).build().toByteArray())};done(status)
        }}
        override fun onCharacteristicWrite(g:BluetoothGatt,c:BluetoothGattCharacteristic,status:Int){handler.post {
            if(g!==gatt)return@post
            val result=writeResult;writeResult=null;result?.invoke(status==0)
            readNext();done(status)
        }}
        @Deprecated("Android compatibility callback")
        override fun onCharacteristicRead(g:BluetoothGatt,c:BluetoothGattCharacteristic,status:Int){
            val bytes=c.value?.clone() ?: byteArrayOf()
            handler.post {
                if(g!==gatt)return@post
                if(status==0 && bytes.isNotEmpty()) {
                    try {
                        val frame=MeshProtos.FromRadio.parseFrom(bytes)
                        if(frame.hasMyInfo())myNode=frame.myInfo.myNodeNum
                        if(frame.hasConfig() && frame.config.hasLora())lora=frame.config.lora
                        if(frame.hasChannel())channels[frame.channel.index]=frame.channel
                        if(frame.hasModuleConfig() && frame.moduleConfig.hasMqtt())mqttEnabled=frame.moduleConfig.mqtt.enabled
                        if(frame.configCompleteId==token && myNode!=0){ready=true;onState("Radio povezan • privatnost i RF profil provjerite u postavkama",true)}
                        onPacket(frame)
                    }catch(_:Exception){onState("Neispravan radio paket odbačen",ready)}
                }
                if(drain.completed(status==0 && bytes.isNotEmpty()))readNext()
                done(status)
            }
        }
        @Deprecated("Android compatibility callback")
        override fun onCharacteristicChanged(g:BluetoothGatt,c:BluetoothGattCharacteristic){handler.post {if(g===gatt && c.uuid==NUM)readNext()}}
    }
    fun startScan(found:(String,String)->Unit):ScanCallback {
        val cb=object:ScanCallback(){override fun onScanResult(type:Int,result:ScanResult){found(result.device.address,result.device.name?:"Meshtastic")}}
        adapter.bluetoothLeScanner?.startScan(listOf(ScanFilter.Builder().setServiceUuid(ParcelUuid(SERVICE)).build()),ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(),cb)
        return cb
    }
    fun stopScan(callback:ScanCallback){try{adapter.bluetoothLeScanner?.stopScan(callback)}catch(_:SecurityException){}}
}
