package org.sigurnisignal
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
@RunWith(AndroidJUnit4::class)
class StoreTest {
 @Test fun durableUncertaintyNeverClosesHelp() {
  val c=InstrumentationRegistry.getInstrumentation().targetContext;c.deleteDatabase("signal.db")
  var db=SecureStore(c);val id=db.enqueue("Trebam pomoć","!12345678",0,true,100)
  assertNotNull(db.reserveNext(1,100));db.close()
  db=SecureStore(c);db.recoverUncertain();assertEquals("uncertain",db.get(id)!!.state)
  assertTrue(db.get(id)!!.open);assertNull(db.reserveNext(2,5000));db.close()
 }
 @Test fun receiptClaimDoesNotConfirmAndRadioAckDoesNotResolve() {
  val c=InstrumentationRegistry.getInstrumentation().targetContext;c.deleteDatabase("signal.db")
  val db=SecureStore(c);val id=db.enqueue("Trebam pomoć","!12345678",0,true,100)
  db.reserveNext(10,100);db.radioAck(10,0);assertEquals("radio_ack",db.get(id)!!.state);assertTrue(db.get(id)!!.open)
  db.receive("!12345678",20,"POTVRDA $id",0,200);assertEquals("radio_ack",db.get(id)!!.state)
  db.humanConfirm(id,"Provjereno uživo");assertTrue(db.get(id)!!.open)
  db.closeHelp(id,"Osoba potvrdila završetak");assertFalse(db.get(id)!!.open);db.close()
 }
}
