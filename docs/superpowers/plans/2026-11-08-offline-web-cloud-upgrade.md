# Sigurni Signal v0.2 web/cloud upgrade implementation

Goal: publish free HTTPS PWA portal, preserve existing BLE/LoRa offline operation, add explicit encrypted planner backups to selected existing Supabase free project and provide read-only isolated LAN distribution.

User authorizes upgrade and public hosting, no payments. Free org already has2activeprojects; hosted DB target awaits user answer. No pause/deletion, paid fallback, radioactivation or existingAuthsettings changes. CloudflareCLIauth confirmed; Netlifyconnectorreauthrequired. PublicAPK/source via GitHub Releases due Pages25MiB assetlimit. ExistingnativeAPK0.1 remains pilotbinary, webversion0.2 distinct.

Approach: static no-CDN modules, IndexedDB planner, serviceworker cacheshell/content only, optional in-memory SupabaseAuth session and client PBKDF2/AES-GCM backup. No cloud private-radio-message/GPS/PSK upload. UIdraftcopy never claims radio send. Localgateway read-only127.0.0.1 default explicitLANbind; stationadmin untouched. All networks need electricalpower; self-managed battery/solar LAN not electricity-free internet.

Tasks:
- [ ] Model/crypto/cloudcontract tests then implementation, byte limits and safe import.
- [ ] Responsive Croatian PWA, offline/checklist/contacts/drafts/guides/downloads/network/cloud views; no fake statuses.
- [ ] Supabase prefixedtable RLS, SQLmigration+cross-owner/anon regression; apply only chosenproject.
- [ ] PubliccontentLANgateway+HTTPsecuritytests and power/topology docs.
- [ ] Browseroffline/crypto/install flows, regressiontests; cleanpublic-sourcepackage and release.
- [ ] Publish CFpages HTTPS+GHrelease, verify liveassets/downloads/CSP/SW, recordcostlimits and unresolvedhardwaretests.

Acceptance: appopensafterfirstinstallationwithoutinternet, localplannerpersists, privatecloudbackuprequirespassphrase+explicitclick; otheraccount/anonRLSdenied; localhost/LANgatewayneverexposesstationAPI/DB; validlivepublicURLs; no nonzeroexpenses. PhysicalRF/autonomy remain unverified.
