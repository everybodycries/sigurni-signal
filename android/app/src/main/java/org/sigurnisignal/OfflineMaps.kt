package org.sigurnisignal

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import org.json.JSONObject
import org.maplibre.android.MapLibre
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.geometry.LatLngBounds
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style
import org.maplibre.android.offline.*

@Composable fun OfflineMapScreen(city:String){
    val context=LocalContext.current
    val owner=LocalLifecycleOwner.current
    val view=remember{MapLibre.getInstance(context);MapView(context).apply{onCreate(null)}}
    var styleUrl by remember{mutableStateOf("")}
    var attribution by remember{mutableStateOf("")}
    var authorized by remember{mutableStateOf(false)}
    var regions by remember{mutableStateOf<List<OfflineRegion>>(emptyList())}
    var status by remember{mutableStateOf("Nema unaprijed instaliranih karata. Nema potvrđenih skloništa.")}
    var downloading by remember{mutableStateOf(false)}
    var activeRegion by remember{mutableStateOf<OfflineRegion?>(null)}
    val manager=remember{OfflineManager.getInstance(context)}
    fun refresh(){manager.listOfflineRegions(object:OfflineManager.ListOfflineRegionsCallback{
        override fun onList(list:Array<OfflineRegion>?){regions=list?.toList() ?: emptyList()}
        override fun onError(error:String){status="Popis karata nije dostupan: $error"}
    })}
    DisposableEffect(owner,view){
        val observer=LifecycleEventObserver{_,event->when(event){
            Lifecycle.Event.ON_START->view.onStart();Lifecycle.Event.ON_RESUME->view.onResume();Lifecycle.Event.ON_PAUSE->view.onPause();Lifecycle.Event.ON_STOP->view.onStop();else->Unit}}
        owner.lifecycle.addObserver(observer)
        onDispose{owner.lifecycle.removeObserver(observer);view.onPause();view.onStop();view.onDestroy()}
    }
    LaunchedEffect(Unit){refresh();view.getMapAsync{map->map.setStyle(Style.Builder().fromJson("""{"version":8,"sources":{},"layers":[{"id":"background","type":"background","paint":{"background-color":"#e8ece6"}}]}"""))}}
    Column(Modifier.fillMaxSize()){
        AndroidView(factory={view},modifier=Modifier.fillMaxWidth().weight(1f))
        Column(Modifier.heightIn(max=300.dp).verticalScroll(rememberScrollState()).padding(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
            Text("Offline karte • $city",style=MaterialTheme.typography.titleLarge)
            Text(status,style=MaterialTheme.typography.bodySmall)
            regions.forEach{region->
                val metadata=runCatching{JSONObject(region.metadata.toString(Charsets.UTF_8))}.getOrNull()
                TextButton(onClick={region.getStatus(object:OfflineRegion.OfflineRegionStatusCallback{
                    override fun onStatus(s:OfflineRegionStatus?){
                        if(s==null){status="Status karte nije dostupan.";return}
                        if(!s.isComplete){status="Paket nije završen; nemojte računati na offline kartu.";return}
                        val definition=region.definition as? OfflineTilePyramidRegionDefinition ?:return
                        val savedStyle=definition.styleURL ?:run{status="Paket nema sačuvan stil.";return}
                        val bounds=definition.bounds ?:run{status="Paket nema granice karte.";return}
                        view.getMapAsync{map->map.setStyle(Style.Builder().fromUri(savedStyle));map.cameraPosition=CameraPosition.Builder().target(bounds.center).zoom(11.0).build()}
                        status="Sačuvana karta: ${metadata?.optString("city")}. ${metadata?.optString("attribution")}. Offline rad pre upotrebe provjerite u zrakoplovnom načinu."
                    }
                    override fun onError(error:String?){status=error ?: "Čitanje sačuvane karte nije uspelo."}
                })}){Text("Otvori ${metadata?.optString("city")?:"paket"}")}
            }
            OutlinedTextField(styleUrl,{styleUrl=it;authorized=false},label={Text("HTTPS URL licenciranog MapLibre stila")},modifier=Modifier.fillMaxWidth())
            OutlinedTextField(attribution,{attribution=it;authorized=false},label={Text("Atribucija i naziv izvora")},modifier=Modifier.fillMaxWidth())
            Row{Checkbox(authorized,{authorized=it});Text("Izvor dozvoljava offline čuvanje. Pripremu pokrećem dok imam internet.",style=MaterialTheme.typography.bodySmall)}
            Button(enabled=authorized&&styleUrl.startsWith("https://")&&attribution.isNotBlank()&&!downloading,onClick={
                val (lat,lon)=when(city){"Kragujevac"->44.0128 to 20.9114;"Sarajevo"->43.8563 to 18.4131;"Beograd"->44.7866 to 20.4489;else->45.8150 to 15.9819}
                val definition=OfflineTilePyramidRegionDefinition(styleUrl,LatLngBounds.from(lat+0.15,lon+0.2,lat-0.15,lon-0.2),8.0,14.0,context.resources.displayMetrics.density)
                val metadata=JSONObject().put("city",city).put("attribution",attribution).put("verified_shelters",0).toString().toByteArray()
                downloading=true;status="Priprema karte pokrenuta. Internet je potreban samo za pripremu."
                manager.createOfflineRegion(definition,metadata,object:OfflineManager.CreateOfflineRegionCallback{
                    override fun onCreate(region:OfflineRegion){
                        activeRegion=region
                        region.setObserver(object:OfflineRegion.OfflineRegionObserver{
                            override fun onStatusChanged(s:OfflineRegionStatus){status="Karta: ${s.completedResourceCount}/${s.requiredResourceCount} resursa";if(s.isComplete){downloading=false;region.setDownloadState(OfflineRegion.STATE_INACTIVE);status="Preuzimanje završeno. Provjerite potpuno offline otvaranje pre oslanjanja na kartu.";refresh()}}
                            override fun onError(error:OfflineRegionError){downloading=false;region.setDownloadState(OfflineRegion.STATE_INACTIVE);status="Preuzimanje nije završeno: ${error.message}"}
                            override fun mapboxTileCountLimitExceeded(limit:Long){downloading=false;region.setDownloadState(OfflineRegion.STATE_INACTIVE);status="Dosegnuto ograničenje paketa ($limit); karta nije spremna."}
                        });region.setDownloadState(OfflineRegion.STATE_ACTIVE)
                    }
                    override fun onError(error:String){downloading=false;status="Karta nije pripremljena: $error"}
                })
            }){Text("Pripremi grad i okolicu")}
            if(downloading)TextButton(onClick={activeRegion?.setDownloadState(OfflineRegion.STATE_INACTIVE);downloading=false;status="Preuzimanje zaustavljeno. Nedovršena karta nije spremna za offline upotrebu."}){Text("Zaustavi pripremu karte")}
            Text("Nema ruta kroz radiološki opasna područja. Označene koordinate nisu potvrda sigurnosti.",style=MaterialTheme.typography.bodySmall)
        }
    }
}
