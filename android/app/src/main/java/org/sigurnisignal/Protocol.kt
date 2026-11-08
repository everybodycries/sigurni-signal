package org.sigurnisignal

import java.security.SecureRandom

/** Readable TEXT_MESSAGE_APP payloads shared with the unmodified iPhone client. */
object Protocol {
    private const val alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
    val idPattern = Regex("^[A-Z2-9]{8}$")
    private val envelope = Regex("^\\[([A-Z2-9]{8})] ([\\s\\S]+)$")
    private val receipt = Regex("^POTVRDA ([A-Z2-9]{8})$")
    fun newId(): String = SecureRandom().let { r -> (1..8).map { alphabet[r.nextInt(32)] }.joinToString("") }
    fun byteCount(text: String): Int = text.toByteArray(Charsets.UTF_8).size
    fun encode(id: String, body: String): String {
        require(idPattern.matches(id)) { "Neispravna oznaka poruke" }
        require(body.isNotBlank() && !body.any { it.code < 32 || it.code == 127 }) { "Prazna ili neispravna poruka" }
        return "[$id] ${body.trim()}".also { require(byteCount(it) <= 200) { "Najviše 200 UTF-8 bajtova s oznakom" } }
    }
    fun decode(text: String): Pair<String, String>? = if (byteCount(text) > 233 || text.any { it.code < 32 || it.code == 127 }) null else envelope.matchEntire(text)?.let { it.groupValues[1] to it.groupValues[2] }
    fun receiptId(text: String): String? = receipt.matchEntire(text)?.groupValues?.get(1)
    fun ttl(help: Boolean) = if (help) 3600L else 86400L
    fun retryDelay(attempts: Int) = when (attempts) { 1 -> 120L; 2 -> 600L; else -> Long.MAX_VALUE }
    fun eligible(created: Long, expires: Long, attempts: Int, lastAttempt: Long?, now: Long): Boolean {
        if (now < created || now >= expires || attempts >= 3) return false
        return attempts == 0 || (lastAttempt != null && now >= lastAttempt && now - lastAttempt >= retryDelay(attempts))
    }
}

/** Preserve a FromNum notification that arrives while a read is already pending. */
internal class ReadDrain {
    var pending=false; private set
    private var signalled=false
    fun request():Boolean {
        if(pending){signalled=true;return false}
        pending=true;return true
    }
    fun completed(hasData:Boolean):Boolean {
        pending=false
        val again=hasData||signalled
        signalled=false
        return again
    }
    fun reset(){pending=false;signalled=false}
}
