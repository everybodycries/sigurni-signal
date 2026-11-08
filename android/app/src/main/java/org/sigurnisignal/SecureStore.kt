package org.sigurnisignal

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class PayloadCipher {
    private val key: SecretKey by lazy {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey("sigurni-signal-v1", null) as? SecretKey) ?: KeyGenerator.getInstance("AES", "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder("sigurni-signal-v1", KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        }.generateKey()
    }
    fun encrypt(text: String): String {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, key) }
        return Base64.encodeToString(cipher.iv + cipher.doFinal(text.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP)
    }
    fun decrypt(encoded: String): String {
        val bytes = Base64.decode(encoded, Base64.NO_WRAP)
        require(bytes.size >= 28)
        return Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, bytes.copyOfRange(0,12))) }
            .doFinal(bytes.copyOfRange(12,bytes.size)).toString(Charsets.UTF_8)
    }
}

data class Message(val id: String, val body: String, val destination: String, val channel: Int, val created: Long,
    val expires: Long, val help: Boolean, val state: String, val attempts: Int, val lastAttempt: Long?, val open: Boolean, val incoming: Boolean)
data class Contact(val node: String, val name: String)

/** Payloads/contact names/audit details encrypted; routing IDs, times and states remain SQLite metadata. */
class SecureStore(context: Context) : SQLiteOpenHelper(context,"signal.db",null,1) {
    private val crypto = PayloadCipher()
    override fun onConfigure(db: SQLiteDatabase) { db.setForeignKeyConstraintsEnabled(true) }
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE messages(id TEXT PRIMARY KEY,body TEXT NOT NULL,destination TEXT NOT NULL,channel INTEGER NOT NULL,created INTEGER NOT NULL,expires INTEGER NOT NULL,help INTEGER NOT NULL,state TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,last_attempt INTEGER,open INTEGER NOT NULL,incoming INTEGER NOT NULL DEFAULT 0)")
        db.execSQL("CREATE TABLE attempts(packet_id INTEGER PRIMARY KEY,message_id TEXT NOT NULL REFERENCES messages(id),created INTEGER NOT NULL)")
        db.execSQL("CREATE TABLE audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,message_id TEXT,at INTEGER NOT NULL,event TEXT NOT NULL,detail TEXT NOT NULL)")
        db.execSQL("CREATE TABLE contacts(node TEXT PRIMARY KEY,name TEXT NOT NULL)")
        db.execSQL("CREATE TABLE meta(key TEXT PRIMARY KEY,value INTEGER NOT NULL)")
    }
    override fun onUpgrade(db: SQLiteDatabase, old: Int, new: Int) { error("Unsupported migration: preserve database") }
    private fun audit(db: SQLiteDatabase,id: String?,event: String,detail: String="", now: Long=System.currentTimeMillis()/1000) {
        db.insertOrThrow("audit",null,ContentValues().apply { put("message_id",id);put("at",now);put("event",event);put("detail",crypto.encrypt(detail)) })
    }
    @Synchronized fun enqueue(body: String,destination: String,channel: Int,help: Boolean,now:Long=System.currentTimeMillis()/1000): String {
        require(destination == "^all" || Regex("^![0-9a-fA-F]{8}$").matches(destination)) { "Odaberite valjan Meshtastic čvor ili ^all" }
        require(channel in 0..7)
        val queued=readableDatabase.rawQuery("SELECT count(*) FROM messages WHERE incoming=0 AND state IN ('queued','submitted','inflight')",null).use { it.moveToFirst();it.getInt(0) }
        require(queued<100) { "Red ima 100 aktivnih poruka. Potreban je pregled prije novih slanja." }
        var id = Protocol.newId()
        while(get(id)!=null) id=Protocol.newId()
        Protocol.encode(id,body)
        val db=writableDatabase; db.beginTransaction()
        try {
            db.insertOrThrow("messages",null,ContentValues().apply {
                put("id",id);put("body",crypto.encrypt(body));put("destination",destination.lowercase());put("channel",channel)
                put("created",now);put("expires",now+Protocol.ttl(help));put("help",if(help)1 else 0);put("state","queued");put("open",if(help)1 else 0)
            })
            audit(db,id,"created",now=now);db.setTransactionSuccessful()
        } finally { db.endTransaction() }
        return id
    }
    @Synchronized fun list(): List<Message> {
        val result=mutableListOf<Message>()
        readableDatabase.rawQuery("SELECT * FROM messages ORDER BY created DESC,id",null).use { c -> while(c.moveToNext()) {
            fun s(key:String)=c.getString(c.getColumnIndexOrThrow(key))
            fun n(key:String)=c.getLong(c.getColumnIndexOrThrow(key))
            result += Message(s("id"),crypto.decrypt(s("body")),s("destination"),n("channel").toInt(),n("created"),n("expires"),n("help")==1L,s("state"),n("attempts").toInt(),if(c.isNull(c.getColumnIndexOrThrow("last_attempt")))null else n("last_attempt"),n("open")==1L,n("incoming")==1L)
        } }
        return result
    }
    @Synchronized fun get(id:String)=list().firstOrNull { it.id==id }
    @Synchronized fun recoverUncertain() {
        val db=writableDatabase
        db.execSQL("UPDATE messages SET state='uncertain' WHERE state='inflight'")
    }
    /** Persist before handing bytes to BLE: a process crash never silently resends an uncertain write. */
    @Synchronized fun reserveNext(packetId:Long,now:Long,allowed:(Message)->Boolean={true}):Message? {
        val db=writableDatabase;db.beginTransaction()
        try {
            val seenClock=db.rawQuery("SELECT value FROM meta WHERE key='last_observed_clock'",null).use { if(it.moveToFirst())it.getLong(0)else null }
            if(seenClock!=null && now<seenClock)return null
            db.execSQL("INSERT OR REPLACE INTO meta(key,value) VALUES('last_observed_clock',?)",arrayOf(now))
            val previous=readableDatabase.rawQuery("SELECT value FROM meta WHERE key='last_send'",null).use { if(it.moveToFirst())it.getLong(0)else null }
            if(previous!=null && (now<previous || now-previous<30)){db.setTransactionSuccessful();return null}
            db.execSQL("UPDATE messages SET state='expired' WHERE incoming=0 AND state IN ('queued','submitted') AND expires<=?",arrayOf(now))
            val next=list().filter { !it.incoming && allowed(it) && it.state in listOf("queued","submitted") && Protocol.eligible(it.created,it.expires,it.attempts,it.lastAttempt,now) }
                .sortedWith(compareByDescending<Message>{it.help}.thenBy{it.created}).firstOrNull()
            if(next==null){db.setTransactionSuccessful();return null}
            db.execSQL("UPDATE messages SET state='inflight', attempts=attempts+1,last_attempt=? WHERE id=?",arrayOf(now,next.id))
            db.insertOrThrow("attempts",null,ContentValues().apply {put("packet_id",packetId);put("message_id",next.id);put("created",now)})
            db.execSQL("INSERT OR REPLACE INTO meta(key,value) VALUES('last_send',?)",arrayOf(now))
            audit(db,next.id,"send_reserved","packet=$packetId",now);db.setTransactionSuccessful()
            return next.copy(state="inflight",attempts=next.attempts+1,lastAttempt=now)
        } finally { db.endTransaction() }
    }
    @Synchronized fun submitted(id:String,success:Boolean) {
        val db=writableDatabase
        // A routing ACK may arrive before the GATT write callback; never regress that state.
        db.execSQL("UPDATE messages SET state=? WHERE id=? AND state='inflight'",arrayOf(if(success)"submitted" else "uncertain",id))
        audit(db,id,if(success)"handed_to_radio" else "write_uncertain")
    }
    @Synchronized fun radioAck(packetId:Long,error:Int) {
        val db=writableDatabase
        val id=db.rawQuery("SELECT message_id FROM attempts WHERE packet_id=?",arrayOf(packetId.toString())).use { if(it.moveToFirst())it.getString(0)else null } ?: return
        db.execSQL("UPDATE messages SET state=? WHERE id=? AND state NOT IN ('human_confirmed','resolved')",arrayOf(if(error==0)"radio_ack"else"radio_error",id))
        audit(db,id,"radio_ack","error=$error (not a human receipt)")
    }
    @Synchronized fun receive(sender:String,packet:Long,text:String,channel:Int,now:Long=System.currentTimeMillis()/1000) {
        if(text.isBlank() || Protocol.byteCount(text)>233)return
        if(text.any { it.code < 32 || it.code == 127 })return
        val decoded=Protocol.decode(text)
        val wireId=decoded?.first ?: Protocol.receiptId(text)
        val id=if(wireId!=null)"rx:$sender:wire:$wireId" else "rx:$sender:packet:$packet"
        val db=writableDatabase
        val previous=get(id)
        if(previous!=null){
            if(previous.body!=text){
                db.execSQL("UPDATE messages SET state='id_collision' WHERE id=?",arrayOf(id))
                audit(db,id,"wire_id_collision","source=$sender; original text preserved",now)
            }
            return
        }
        val incomingHelp=decoded?.second?.uppercase()?.let{it.startsWith("TREBAM POMOĆ")||it.startsWith("TREBAM POMOC")} ?: false
        db.insertOrThrow("messages",null,ContentValues().apply {
            put("id",id);put("body",crypto.encrypt(text));put("destination",sender);put("channel",channel);put("created",now);put("expires",now+86400)
            put("help",if(incomingHelp)1 else 0);put("state",if(Protocol.receiptId(text)!=null)"unverified_receipt"else"received");put("open",if(incomingHelp)1 else 0);put("incoming",1)
        })
        audit(db,id,"received_unverified","source=$sender")
        // Do not parse a POTVRDA claim into a human-confirmed state.
    }
    @Synchronized fun humanConfirm(id:String,note:String) {
        require(note.isNotBlank())
        val m=get(id)?:error("Unknown message");require(!m.incoming)
        val db=writableDatabase;db.execSQL("UPDATE messages SET state='human_confirmed' WHERE id=?",arrayOf(id));audit(db,id,"human_verified",note)
    }
    @Synchronized fun closeHelp(id:String,note:String) {
        require(note.isNotBlank());val m=get(id)?:error("Unknown message");require(m.help && m.open)
        val db=writableDatabase;db.execSQL("UPDATE messages SET open=0,state='resolved' WHERE id=?",arrayOf(id));audit(db,id,"help_closed_by_person",note)
    }
    @Synchronized fun pause(id:String) { writableDatabase.execSQL("UPDATE messages SET state='paused' WHERE id=? AND state IN ('queued','submitted')",arrayOf(id));audit(writableDatabase,id,"paused_by_user") }
    @Synchronized fun contacts():List<Contact> = readableDatabase.rawQuery("SELECT node,name FROM contacts ORDER BY node",null).use { c -> buildList { while(c.moveToNext())add(Contact(c.getString(0),crypto.decrypt(c.getString(1)))) } }
    @Synchronized fun saveContact(node:String,name:String) { require(Regex("^![0-9a-fA-F]{8}$").matches(node));require(name.isNotBlank()&&name.length<=80);writableDatabase.insertWithOnConflict("contacts",null,ContentValues().apply {put("node",node.lowercase());put("name",crypto.encrypt(name))},SQLiteDatabase.CONFLICT_REPLACE) }
    @Synchronized fun recordPublicConsent(exactText:String,destination:String) {
        require(exactText.isNotBlank() && Protocol.byteCount(exactText)<=200 && !exactText.any { it.code<32 || it.code==127 });require(destination in listOf("Zagreb","Sarajevo","Beograd"))
        audit(writableDatabase,null,"public_draft_consented","destination=$destination\nexact_text=$exactText")
    }
}
