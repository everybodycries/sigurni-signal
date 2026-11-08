package org.sigurnisignal
import org.junit.Assert.*
import org.junit.Test
class ProtocolTest {
    @Test fun wireFixtures() {
        assertEquals("[A7K42P9Q] DOBRO SAM", Protocol.encode("A7K42P9Q", "DOBRO SAM"))
        assertEquals(20, Protocol.byteCount(Protocol.encode("A7K42P9Q", "DOBRO SAM")))
        assertEquals(24, Protocol.byteCount(Protocol.encode("BBBBBBBB", "Trebam pomoć")))
    }
    @Test fun utf8Boundary() {
        assertEquals(200, Protocol.byteCount(Protocol.encode("AAAAAAAA", "a".repeat(187) + "ć")))
        assertThrows(IllegalArgumentException::class.java) { Protocol.encode("AAAAAAAA", "a".repeat(188) + "ć") }
        assertEquals("AAAAAAAA", Protocol.decode("[AAAAAAAA] " + "a".repeat(222))?.first)
        assertNull(Protocol.decode("[AAAAAAAA] " + "a".repeat(223)))
    }
    @Test fun ttlAndAttemptLimits() {
        assertEquals(3600L, Protocol.ttl(true)); assertEquals(86400L, Protocol.ttl(false))
        assertTrue(Protocol.eligible(100,3700,0,null,100))
        assertFalse(Protocol.eligible(100,3700,0,null,99))
        assertFalse(Protocol.eligible(100,3700,1,100,219))
        assertTrue(Protocol.eligible(100,3700,1,100,220))
        assertTrue(Protocol.eligible(100,3700,2,220,820))
        assertFalse(Protocol.eligible(100,3700,3,820,2000))
        assertFalse(Protocol.eligible(100,3700,1,100,3700))
    }
    @Test fun receiptsAreOnlyTextClaims() { assertEquals("A7K42P9Q", Protocol.receiptId("POTVRDA A7K42P9Q")); assertNull(Protocol.receiptId("POTVRDA anything")) }
    @Test fun rejectsAllAsciiControls() { (0..31).plus(127).forEach { code -> assertThrows(IllegalArgumentException::class.java) { Protocol.encode("AAAAAAAA", "a"+code.toChar()+"b") } } }
    @Test fun rejectsMalformed() { assertThrows(IllegalArgumentException::class.java) { Protocol.encode("bad", "text") }; assertThrows(IllegalArgumentException::class.java) { Protocol.encode("AAAAAAAA", "\u0000") } }
    @Test fun notificationDuringEmptyReadIsNotLost() {
        val d=ReadDrain()
        assertTrue(d.request())
        assertFalse(d.request())
        assertTrue(d.completed(false))
        assertTrue(d.request())
        assertFalse(d.completed(false))
        assertTrue(d.request())
        assertTrue(d.completed(true))
        d.reset(); assertTrue(d.request())
    }
}
