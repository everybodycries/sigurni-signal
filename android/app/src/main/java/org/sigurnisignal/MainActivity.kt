package org.sigurnisignal

import android.Manifest
import android.annotation.SuppressLint
import android.content.*
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.json.JSONObject
import java.time.*
import java.time.format.DateTimeFormatter

private val Ink=Color(0xff172832)
private val Teal=Color(0xff12695e)
private val Paper=Color(0xfff4f3ee)

class MainActivity:ComponentActivity() {
    private val permissionRequest=registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()){Runtime.changed()}
    override fun onCreate(savedInstanceState:Bundle?){super.onCreate(savedInstanceState);setContent{
        MaterialTheme(colorScheme=lightColorScheme(primary=Teal,secondary=Ink,background=Paper,surface=Color.White,error=Color(0xffb5352d))){ SignalApp(::permissions) }
    }}
    private fun permissions(){
        val required=mutableListOf<String>()
        if(Build.VERSION.SDK_INT>=31)required+=listOf(Manifest.permission.BLUETOOTH_SCAN,Manifest.permission.BLUETOOTH_CONNECT)
        else required+=Manifest.permission.ACCESS_FINE_LOCATION
        if(Build.VERSION.SDK_INT>=33)required+=Manifest.permission.POST_NOTIFICATIONS
        permissionRequest.launch(required.toTypedArray())
    }
}

@Composable private fun SignalApp(requestPermissions:()->Unit) {
    val context=LocalContext.current
    val db=remember{Runtime.database(context)}
    val runtime by Runtime.state.collectAsStateWithLifecycle()
    var tab by remember{mutableStateOf(0)}
    var composeHelp by remember{mutableStateOf<Boolean?>(null)}
    var error by remember{mutableStateOf<String?>(null)}
    val prefs=remember{context.getSharedPreferences("settings",Context.MODE_PRIVATE)}
    var city by remember{mutableStateOf(prefs.getString("city","Kragujevac")!!)}
    val messages=remember(runtime.revision){db.list()}
    Scaffold(containerColor=Paper,topBar={Column(Modifier.background(Ink).fillMaxWidth().padding(20.dp)){
        Row(verticalAlignment=Alignment.CenterVertically){Text("◉",color=Color(0xffa6d88c),fontSize=26.sp);Spacer(Modifier.width(10.dp));Text("SIGURNI SIGNAL",color=Color.White,fontWeight=FontWeight.Bold,letterSpacing=2.sp)}
        Spacer(Modifier.height(8.dp));Text("$city  /  OFFLINE PILOT",color=Color(0xffa9bdc2),fontSize=11.sp,letterSpacing=1.sp)
    }},bottomBar={NavigationBar(containerColor=Color.White){
        val labels=listOf("Pregled","Poruke","Karta","Priprema","Baza")
        val icons=listOf("◇","▤","⌖","▣","⇄")
        labels.forEachIndexed{i,title->NavigationBarItem(selected=tab==i,onClick={tab=i},icon={Text(icons[i],fontSize=23.sp)},label={Text(title,fontSize=10.sp)})}
    }}){padding->
        Column(Modifier.padding(padding).fillMaxSize()) {
            Surface(color=if(runtime.connected)Color(0xffdcebdc)else Color(0xffffe9c8),modifier=Modifier.fillMaxWidth()){
                Text(runtime.link,Modifier.padding(horizontal=16.dp,vertical=9.dp),fontSize=12.sp,color=Ink)
            }
            if(tab==2){OfflineMapScreen(city);return@Column}
            Column(Modifier.verticalScroll(rememberScrollState()).padding(18.dp),verticalArrangement=Arrangement.spacedBy(14.dp)){
                when(tab){
                    0->{
                        Text("Ostanimo povezani.",fontSize=30.sp,lineHeight=34.sp,fontWeight=FontWeight.Bold,color=Ink)
                        Text("Poruke putuju radiom. Primitak i pomoć trebaju zasebnu ljudsku potvrdu.",color=Color(0xff53646a))
                        Button(onClick={composeHelp=true},colors=ButtonDefaults.buttonColors(containerColor=Color(0xffb5352d)),shape=RoundedCornerShape(14.dp),modifier=Modifier.fillMaxWidth().height(62.dp)){
                            Text("+",fontSize=25.sp);Spacer(Modifier.width(12.dp));Text("TREBAM POMOĆ",fontWeight=FontWeight.Bold)
                        }
                        OutlinedButton(onClick={composeHelp=false},shape=RoundedCornerShape(14.dp),modifier=Modifier.fillMaxWidth().height(54.dp)){Text("✓",fontSize=23.sp);Spacer(Modifier.width(12.dp));Text("Dobro sam")}
                        val phoneBattery=(context.getSystemService(Context.BATTERY_SERVICE) as android.os.BatteryManager).getIntProperty(android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY)
                        InfoCard("Napajanje","Telefon: ${if(phoneBattery in 0..100)"$phoneBattery %" else "nepoznato"} • Radio: ${runtime.radioBattery?:"telemetrija nije primljena"}")
                        InfoCard("Otvoreni zahtevi", "${messages.count{it.help&&it.open}} zahteva • istek slanja ih ne zatvara")
                        InfoCard("Sljedeća veza baza",nextWindow()+" • dogovoreni termini 08 / 14 / 20 h")
                        InfoCard("Priprema pre prekida", "Napunite radio i powerbank. Provjerite privatni kanal, kontakte i sačuvane karte.")
                        Text("Međugradske veze i autonomija nisu terenski potvrđene. Ovo nije veza sa službom 112.",fontSize=12.sp,color=MaterialTheme.colorScheme.error)
                        RadioSettings(requestPermissions,city,{city=it;prefs.edit().putString("city",it).apply()})
                    }
                    1->{
                        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text("Poruke",fontSize=26.sp,fontWeight=FontWeight.Bold);TextButton(onClick={composeHelp=false}){Text("Nova poruka")}}
                        Text("Radijska potvrda ≠ lični primitak. Prikazani pošiljatelji nisu službeno ovjereni.",fontSize=12.sp)
                        if(messages.isEmpty())InfoCard("Još nema poruka","Poruke ostaju sačuvane i kad radio nije povezan.")
                        messages.forEach{m->MessageCard(m,db){Runtime.changed()}}
                        Contacts(db)
                    }
                    3->{ Text("Priprema i uputstva",fontSize=26.sp,fontWeight=FontWeight.Bold);Guides() }
                    4->{
                        Text("Veza s bazom",fontSize=26.sp,fontWeight=FontWeight.Bold)
                        InfoCard("Međugradski prenos je ručan","Baza mora imati proverene operatere, propise i izmjerenu vezu. HF poruke nisu privatni razgovor.")
                        PublicRadiogram(db)
                        RadioSettings(requestPermissions,city,{city=it;prefs.edit().putString("city",it).apply()})
                    }
                }
                (error?:runtime.error)?.let{Text(it,color=MaterialTheme.colorScheme.error)}
                Spacer(Modifier.height(12.dp))
            }
        }
    }
    composeHelp?.let{help->Composer(help,db,onDismiss={composeHelp=null},onCreated={composeHelp=null;tab=1;Runtime.changed()})}
}

@Composable private fun InfoCard(title:String,body:String){Card(colors=CardDefaults.cardColors(containerColor=Color.White),shape=RoundedCornerShape(14.dp),modifier=Modifier.fillMaxWidth()){
    Column(Modifier.padding(17.dp),verticalArrangement=Arrangement.spacedBy(7.dp)){Text(title,fontWeight=FontWeight.SemiBold,color=Ink);Text(body,fontSize=13.sp,color=Color(0xff53646a),lineHeight=19.sp)}
}}
private fun stamp(epoch:Long):String=DateTimeFormatter.ofPattern("dd.MM. HH:mm").withZone(ZoneId.systemDefault()).format(Instant.ofEpochSecond(epoch))
private fun nextWindow():String {
    val zone=ZoneId.of("Europe/Belgrade");val now=ZonedDateTime.now(zone)
    for(day in 0L..1L)for(hour in listOf(8,14,20)){
        val start=now.toLocalDate().plusDays(day).atTime(hour,0).atZone(zone)
        if(now>=start && now<start.plusMinutes(30))return "Termin u toku do ${start.plusMinutes(30).toLocalTime()}"
        if(start>now)return stamp(start.toEpochSecond())
    }
    return "Vreme nije dostupno"
}

@Composable private fun Composer(help:Boolean,db:SecureStore,onDismiss:()->Unit,onCreated:()->Unit){
    val context=LocalContext.current
    var body by remember{mutableStateOf(if(help)"TREBAM POMOĆ: " else "DOBRO SAM")}
    var destination by remember{mutableStateOf("")};var channel by remember{mutableStateOf("0")}
    var error by remember{mutableStateOf("")};var confirmed by remember{mutableStateOf(false)}
    var countdown by remember{mutableStateOf(0)}
    val locationPermission=androidx.activity.compose.rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()){error="Lokacija nije umetnuta. Ponovno pritisnite Umetni lokaciju nakon dozvole."}
    LaunchedEffect(countdown){if(countdown>0){kotlinx.coroutines.delay(1000);if(countdown==1){try{db.enqueue(body.trim(),destination.trim(),channel.toInt(),help);onCreated()}catch(e:Exception){error=e.message?:"Čuvanje nije uspelo"};countdown=0}else countdown--}}
    AlertDialog(onDismissRequest={if(countdown==0)onDismiss()},title={Text(if(help)"Zahtev za pomoć"else"Nova poruka")},text={Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(9.dp)){
        Text("Poruka ne kontaktira 112. Bez odredišnog radija nema isporuke.",fontSize=12.sp)
        OutlinedTextField(destination,{destination=it;confirmed=false},label={Text("Odredište !12345678 ili ^all")},enabled=countdown==0,singleLine=true)
        val contacts=remember{db.contacts()};contacts.forEach{c->TextButton(enabled=countdown==0,onClick={destination=c.node;confirmed=false}){Text("${c.name} • ${c.node}")}}
        OutlinedTextField(channel,{channel=it;confirmed=false},label={Text("Indeks proverenog privatnog kanala 0–7")},enabled=countdown==0)
        OutlinedTextField(body,{body=it;confirmed=false},label={Text("Tačan tekst poruke")},minLines=3,enabled=countdown==0)
        Text("${Protocol.byteCount("[AAAAAAAA] "+body.trim())} / 200 UTF-8 bajtova",fontSize=12.sp)
        TextButton(onClick={
            if(ContextCompat.checkSelfPermission(context,Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED){locationPermission.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION))}
            else {try{val lm=context.getSystemService(Context.LOCATION_SERVICE)as LocationManager
                @SuppressLint("MissingPermission") val loc=lm.getLastKnownLocation(LocationManager.GPS_PROVIDER)
                if(loc==null || (android.os.SystemClock.elapsedRealtimeNanos()-loc.elapsedRealtimeNanos) !in 0L..300000000000L)error="Nema svježe GPS lokacije. Lokacija nije dodana."
                else {body += " ${String.format(java.util.Locale.US,"%.5f,%.5f",loc.latitude,loc.longitude)}";confirmed=false;error="Lokacija je samo u nacrtu. Provjerite tekst pre slanja."}
            }catch(_:Exception){error="GPS nije dostupan. Lokacija nije dodana."}}
        },enabled=countdown==0){Text("Umetni moju lokaciju (po želji)")}
        Row(verticalAlignment=Alignment.CenterVertically){Checkbox(confirmed,{confirmed=it},enabled=countdown==0);Text("Provjerio/la sam primaoca i tačan tekst.",fontSize=12.sp)}
        if(countdown>0)Text("Slanje za $countdown s — možete poništiti.",color=MaterialTheme.colorScheme.error)
        if(error.isNotEmpty())Text(error,color=MaterialTheme.colorScheme.error,fontSize=12.sp)
    }},confirmButton={Button(enabled=confirmed&&countdown==0,onClick={
        try{Protocol.encode("AAAAAAAA",body.trim());require(destination=="^all"||Regex("^![0-9a-fA-F]{8}$").matches(destination.trim())){"Provjerite odredište"};require(channel.toInt()in 0..7);countdown=5}
        catch(e:Exception){error=e.message?:"Provjerite unos"}
    }){Text("Sačuvaj za slanje")}},dismissButton={TextButton(onClick={countdown=0;onDismiss()}){Text("Poništi")}})
}

@Composable private fun MessageCard(m:Message,db:SecureStore,changed:()->Unit){
    var action by remember{mutableStateOf<String?>(null)};var note by remember{mutableStateOf("")}
    val now=System.currentTimeMillis()/1000
    val label=when(m.state){"queued"->"Čeka radio";"inflight"->"Predaja u toku";"submitted"->"Predato radiju • nije potvrda primitka";"radio_ack"->"Radijska potvrda • osoba nije potvrđena";"human_confirmed"->"Lično proveren primitak";"uncertain"->"Predaja nepoznata • treba pregled";"expired"->"Istek ponovnog slanja";"paused"->"Slanje zaustavljeno";"radio_error"->"Radio je prijavio pogrešku";"received"->"Primljeno • neprovjeren pošiljalac";"unverified_receipt"->"Nepotvrđena tvrdnja o primitku";"id_collision"->"Sukob oznake poruke • potreban pregled";"resolved"->"Zahtev ručno zatvoren";else->m.state}
    Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Color.White)){
        Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
            Text("${if(m.incoming)"OD"else"ZA"} ${m.destination}  ·  ${stamp(m.created)}",fontSize=11.sp,color=Teal)
            Text(m.body,color=Ink,fontSize=16.sp)
            Text(label,fontWeight=FontWeight.SemiBold,fontSize=12.sp)
            if(!m.incoming){
                Text("${m.id} • pokušaji ${m.attempts}/3",fontSize=11.sp)
                if(now<m.created)Text("Vreme uređaja je vraćeno. Slanje čeka pregled sata.",color=MaterialTheme.colorScheme.error,fontSize=12.sp)
                if(now>=m.expires)Text("Rok slanja istekao. ${if(m.open)"Zahtev ostaje OTVOREN."else""}",color=MaterialTheme.colorScheme.error,fontSize=12.sp)
                if(m.attempts>=3 && m.state=="submitted")Text("Pokušaji iscrpljeni. Potreban je lični pregled.",fontSize=12.sp)
                if(m.state in listOf("queued","submitted"))TextButton(onClick={db.pause(m.id);changed()}){Text("Zaustavi ponovno slanje")}
                TextButton(onClick={action="confirm"}){Text("Lično proveri primitak")}
            }
            if(m.help&&m.open){
                Text("Zahtev ostaje OTVOREN dok ga čovjek ne zatvori.",fontSize=12.sp,color=MaterialTheme.colorScheme.error)
                TextButton(onClick={action="close"}){Text("Ručno zatvori zahtev")}
            }
        }
    }
    if(action!=null)AlertDialog(onDismissRequest={action=null},title={Text(if(action=="close")"Zatvaranje zahteva"else"Ljudska potvrda")},text={Column{Text("Ova radnja je vaša evidencija, ne jamstvo dolaska pomoći. Zapišite s kim i kako je provereno.");OutlinedTextField(note,{note=it},label={Text("Bilješka provere")})}},confirmButton={TextButton(enabled=note.isNotBlank(),onClick={if(action=="close")db.closeHelp(m.id,note)else db.humanConfirm(m.id,note);changed();action=null;note=""}){Text("Zabeleži")}},dismissButton={TextButton(onClick={action=null}){Text("Odustani")}})
}

@Composable private fun Contacts(db:SecureStore){
    var name by remember{mutableStateOf("")};var node by remember{mutableStateOf("")};var error by remember{mutableStateOf("")};var revision by remember{mutableStateOf(0)}
    Text("Lokalni imenik",fontSize=20.sp,fontWeight=FontWeight.Bold)
    remember(revision){db.contacts()}.forEach{Text("${it.name} · ${it.node}",fontSize=13.sp)}
    OutlinedTextField(name,{name=it},label={Text("Ime kontakta")},modifier=Modifier.fillMaxWidth())
    OutlinedTextField(node,{node=it},label={Text("Radio oznaka !12345678")},modifier=Modifier.fillMaxWidth())
    TextButton(onClick={try{db.saveContact(node.trim(),name.trim());name="";node="";revision++;error=""}catch(_:Exception){error="Provjerite ime i radio oznaku."}}){Text("Sačuvaj kontakt")}
    if(error.isNotEmpty())Text(error,color=MaterialTheme.colorScheme.error)
}

@Composable private fun RadioSettings(requestPermissions:()->Unit,city:String,onCity:(String)->Unit){
    val context=LocalContext.current
    val prefs=remember{context.getSharedPreferences("settings",Context.MODE_PRIVATE)}
    var reviewed by remember{mutableStateOf(prefs.getBoolean("rf_reviewed",false))}
    var address by remember{mutableStateOf(prefs.getString("address","")!!)}
    var found by remember{mutableStateOf(mapOf<String,String>())}
    var scanning by remember{mutableStateOf(false)}
    var scanError by remember{mutableStateOf("")}
    val scanner=remember{MeshtasticBle(context,{_,_->},{})}
    var callback by remember{mutableStateOf<android.bluetooth.le.ScanCallback?>(null)}
    DisposableEffect(Unit){onDispose{callback?.let{scanner.stopScan(it)};scanner.close()}}
    LaunchedEffect(scanning){if(scanning){kotlinx.coroutines.delay(12000);callback?.let{scanner.stopScan(it)};scanning=false}}
    HorizontalDivider()
    Text("Radio i lokalni profil",fontSize=20.sp,fontWeight=FontWeight.Bold)
    Row(Modifier.horizontalScroll(rememberScrollState())){listOf("Kragujevac","Zagreb","Sarajevo","Beograd").forEach{c->FilterChip(selected=c==city,onClick={onCity(c)},label={Text(c)},modifier=Modifier.padding(end=6.dp))}}
    Text("Radio unaprijed konfigurirajte službenim klijentom: dozvoljen RF profil, duty-cycle ograničenje i privatni kanal bez javnog zadanog ključa. Zatim odspojite službeni klijent.",fontSize=12.sp)
    Row(verticalAlignment=Alignment.CenterVertically){Checkbox(reviewed,{reviewed=it;prefs.edit().putBoolean("rf_reviewed",it).putLong("rf_reviewed_at",System.currentTimeMillis()/1000).apply()});Text("Provjerio/la sam lokalne propise, podešavanja radija i privatni kanal. Dopuštam slanje reda poruka.",fontSize=12.sp)}
    if(!reviewed)Text("Slanje reda je zaključano. Nema automatskog odabira frekvencije.",color=MaterialTheme.colorScheme.error,fontSize=12.sp)
    TextButton(onClick=requestPermissions){Text("Dopusti Bluetooth i obaveštenja")}
    OutlinedTextField(address,{address=it},label={Text("BLE adresa (odabir ispod ili ručno)")},modifier=Modifier.fillMaxWidth())
    Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){
        OutlinedButton(enabled=!scanning,onClick={try{
            val required=if(Build.VERSION.SDK_INT>=31)Manifest.permission.BLUETOOTH_SCAN else Manifest.permission.ACCESS_FINE_LOCATION
            require(ContextCompat.checkSelfPermission(context,required)==PackageManager.PERMISSION_GRANTED){"Najpre dopustite Bluetooth pretragu"}
            found=emptyMap();scanning=true;scanError=""
            callback=scanner.startScan{mac,name->android.os.Handler(android.os.Looper.getMainLooper()).post{found=found+(mac to name)}}
        }catch(e:Exception){scanning=false;scanError=e.message?:"Uključite Bluetooth i dopustite pretragu."}}){Text(if(scanning)"Pretražujem…"else"Pronađi radio")}
        Button(onClick={try{
            require(android.bluetooth.BluetoothAdapter.checkBluetoothAddress(address.trim())){"Provjerite BLE adresu"}
            if(Build.VERSION.SDK_INT>=31)require(ContextCompat.checkSelfPermission(context,Manifest.permission.BLUETOOTH_CONNECT)==PackageManager.PERMISSION_GRANTED){"Dopustite Bluetooth povezivanje"}
            prefs.edit().putString("address",address.trim()).apply()
            callback?.let{scanner.stopScan(it)};scanning=false
            ContextCompat.startForegroundService(context,Intent(context,RadioService::class.java).putExtra("address",address.trim()))
        }catch(e:Exception){scanError=e.message?:"Povezivanje nije uspelo"}}){Text("Poveži")}
    }
    found.forEach{(mac,name)->TextButton(onClick={address=mac}){Text("$name · $mac")}}
    TextButton(onClick={context.stopService(Intent(context,RadioService::class.java))}){Text("Odspoji radio i zaustavi servis")}
    if(scanError.isNotEmpty())Text(scanError,color=MaterialTheme.colorScheme.error,fontSize=12.sp)
    Text("Prisilno zatvaranje aplikacije prekida obradu. Ne pretpostavljajte da će radio sačuvati propuštene poruke. Za kritične poruke dogovorite ljudsku potvrdu i samostalan radijski alarm.",fontSize=12.sp)
}

@Composable private fun PublicRadiogram(db:SecureStore){
    val context=LocalContext.current
    var text by remember{mutableStateOf("")};var city by remember{mutableStateOf("Sarajevo")};var consent by remember{mutableStateOf(false)}
    var pending by remember{mutableStateOf<String?>(null)};var status by remember{mutableStateOf("")}
    val export=androidx.activity.compose.rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")){uri->
        if(uri!=null && pending!=null)try{context.contentResolver.openOutputStream(uri)?.use{it.write(pending!!.toByteArray(Charsets.UTF_8))}?:error("Nije moguće otvoriti datoteku");status="Nacrt sačuvan za ličnu predaju operateru. Nije radijski poslan."}catch(_:Exception){status="Izvoz nije uspeo."}
        pending=null
    }
    Text("Zaseban javni radiogram",fontWeight=FontWeight.Bold)
    Text("Unesite samo tekst namijenjen javnom emitiranju. Nemojte kopirati privatni razgovor ili osjetljive podatke. Operater odlučuje o dopuštenosti i prenosu.",fontSize=12.sp)
    Row{listOf("Kragujevac","Zagreb","Sarajevo","Beograd").forEach{c->FilterChip(selected=city==c,onClick={city=c;consent=false},label={Text(c)},modifier=Modifier.padding(end=4.dp))}}
    OutlinedTextField(text,{text=it;consent=false},label={Text("Tačan javni tekst")},minLines=3,modifier=Modifier.fillMaxWidth())
    Text("JAVNI PREGLED → $city\n$text",fontSize=13.sp,color=Ink)
    Text("${Protocol.byteCount(text)} / 200 UTF-8 bajtova",fontSize=12.sp)
    Row(verticalAlignment=Alignment.CenterVertically){Checkbox(consent,{consent=it});Text("Izričito pristajem na javno emitovanje tačno ovog teksta za izabrani grad.",fontSize=12.sp)}
    Button(enabled=consent&&text.isNotBlank()&&Protocol.byteCount(text)<=200&&!text.any{it.code<32||it.code==127},onClick={
        try {
        db.recordPublicConsent(text,city)
        pending=JSONObject().put("version",1).put("destination_city",city).put("exact_text",text).put("consent",true).put("consented_at",Instant.now().toString()).put("status","draft_not_transmitted").toString(2)
        export.launch("javni-radiogram-${System.currentTimeMillis()}.json")
        } catch(e:Exception) { status=e.message?:"Nacrt nije sačuvan." }
    }){Text("Sačuvaj nacrt za operatera")}
    if(status.isNotEmpty())Text(status,fontSize=12.sp)
}

@Composable private fun Guides(){
    val context=LocalContext.current
    val data=remember{runCatching{JSONObject(context.assets.open("guides.json").bufferedReader().readText())}.getOrNull()}
    InfoCard("Pilot-sadržaj za pripremu","Pre upotrebe potreban je lokalni stručni pregled. Aktualne uputstva nadležnih službi imaju prednost. Telefon ne mjeri zračenje.")
    if(data==null){Text("Paket uputstava nije dostupan. Provjerite instalaciju.");return}
    Text("Paket ${data.optString("version")} • ${data.optString("updated_at")}",fontSize=12.sp)
    val guides=data.getJSONArray("guides")
    for(i in 0 until guides.length()){
        val guide=guides.getJSONObject(i);var expanded by remember(guide.optString("id")){mutableStateOf(false)}
        Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Color.White)){
            Column(Modifier.padding(16.dp)){
                TextButton(onClick={expanded=!expanded}){Text(guide.getString("title"),fontWeight=FontWeight.Bold)}
                if(expanded){
                    val sections=guide.getJSONArray("sections")
                    for(j in 0 until sections.length()){val s=sections.getJSONObject(j);Text(s.getString("heading"),fontWeight=FontWeight.SemiBold);Text(s.getString("text"),Modifier.padding(vertical=8.dp),fontSize=14.sp,lineHeight=20.sp)}
                    Text("Status pregleda: ${guide.optString("review_status")}",fontSize=11.sp)
                    val sources=guide.getJSONArray("sources")
                    for(j in 0 until sources.length()){val s=sources.getJSONObject(j);Text("${s.getString("title")}\n${s.getString("url")}",Modifier.padding(top=8.dp),fontSize=11.sp)}
                }
            }
        }
    }
}
