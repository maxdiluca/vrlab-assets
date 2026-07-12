# VR Lab Equipment Kiosk

An iPad-friendly homepage for checking VR Lab equipment in and out through Assetbots. The page provides concise instructions and five large destinations:

- Visitor cards
- Headsets
- IT equipment (computers and monitors)
- Various equipment
- Storage-room equipment

The site is dependency-free and suitable for GitHub Pages.

## Security model

This repository is public, but Assetbots kiosk launch URLs can grant limited access to a database. The URLs are therefore **not committed to this repository**. They are entered once on the lab iPad and stored in that browser's `localStorage`.

- The page sends no analytics or network requests.
- It accepts only HTTPS URLs on `assetbots.com` or one of its subdomains.
- Clearing Safari website data removes the saved destinations.
- Browser storage protects the links from public source-code disclosure; it is not enterprise secret storage and does not protect against someone with physical or administrative access to the iPad.
- Use Assetbots kiosk launch URLs with limited Borrower-level access. Never configure a personal or administrator session on a shared device.

## 1. Prepare Assetbots

First confirm the lab's current entitlement and account structure. As of July 2026, Assetbots advertises a Free plan with 200 assets, one administrator and one database. Its terms also require one account per company. Do not create additional free accounts to bypass plan limits.

The recommended structure is one database with five asset categories and either one universal kiosk or five filtered kiosks. If Assetbots has explicitly authorised a legacy multi-database arrangement, this homepage can also link to one kiosk in each database.

For each destination:

1. Open the database as an administrator.
2. Under **Assets**, open **Kiosks** and create a kiosk.
3. Give it a clear name and restrict assets and people with search filters.
4. Save it, then use **More actions → Copy Launch URL**.
5. Sign out of the administrator account and test the URL in a private browser. Confirm that it permits only the intended checkout/check-in workflow and does not expose administrative controls.

Official references:

- [Assetbots kiosks](https://help.assetbots.com/article/53-kiosks)
- [Kiosk launch URLs and limited access](https://www.assetbots.com/blog/announcing-kiosks)
- [Check-in and checkout](https://help.assetbots.com/article/13-check-in-and-checkout)
- [Current pricing](https://www.assetbots.com/pricing)
- [Account terms](https://www.assetbots.com/terms)

## 2. Publish with GitHub Pages

The production site can be published directly from the root of the repository's `main` branch.

1. Open the repository on GitHub.
2. Go to **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Select `main`, `/ (root)`, then **Save**.
5. Wait for GitHub to report the live URL.

No build step is required.

## 3. Configure the lab iPad

On the iPad that will remain at the entrance:

1. Open the live homepage in Safari, adding `?setup=1` to the address. For example:

   `https://maxdiluca.github.io/vrlab-assets/?setup=1`

2. Paste the five tested Assetbots kiosk launch URLs and select **Save and open homepage**.
3. Open each tile and complete a test checkout and check-in.
4. Return to the homepage, tap Safari's **Share** button, then **Add to Home Screen**.
5. Grant camera access when Assetbots first asks to scan a QR code.
6. Use iPad Guided Access or the University's device-management controls to keep the device in the approved workflow.

To replace or remove links, revisit `?setup=1`. Configure the same URLs again if Safari website data is cleared or the iPad is replaced.

## Instructions for borrowers

1. Select the correct equipment group.
2. In Assetbots, select **Checkout** to borrow equipment or **Check In** to return it.
3. For checkout, find your Person record.
4. Scan each item's QR label or search by asset tag.
5. Review every item and confirm the action.
6. Wait for the success message, then use Back to return to the homepage.

If the correct person or item is missing, users should stop and ask a member of VR Lab staff rather than selecting a similar record.

## Weekly minimized backup

The repository includes a macOS weekly backup task for the five current Assetbots databases. It runs on Mondays at 07:00 local time and writes dated, checksummed JSON snapshots to:

`Equipment queries/Assetbots Backups`

This folder is outside the Git repository but inside the lab's University shared library, so OneDrive can synchronise it. Confirm that access to the destination is restricted to the appropriate lab asset administrators.

The automated snapshot contains:

- database metadata;
- assets, with any related Person reduced to name and email;
- People reduced strictly to name and email;
- locations; and
- record counts and SHA-256 checksums.

It excludes API keys, all other Person fields, notes, attachments, complete checkout history and database configuration. It therefore supplements rather than replaces periodic native Excel exports and separate preservation of important attachments.

### One-time API-key setup

1. In each Assetbots database, open **Settings → API Keys** and create a **Reader** key.
2. Run the Keychain setup script in Terminal. Paste each key only into the protected Keychain prompt—never into this repository or a chat:

   ```sh
   ./scripts/configure_assetbots_keys.sh
   ```

3. Validate the five keys without writing a backup:

   ```sh
   python3 scripts/assetbots_backup.py \
     --output-root "../Equipment queries/Assetbots Backups" \
     --dry-run
   ```

4. Install the weekly task:

   ```sh
   python3 scripts/manage_weekly_backup.py install
   ```

5. Create and validate the first backup:

   ```sh
   python3 scripts/manage_weekly_backup.py run-now
   python3 scripts/assetbots_backup.py \
     --validate "../Equipment queries/Assetbots Backups/<dated-folder>"
   ```

Inspect the task with `python3 scripts/manage_weekly_backup.py status` or remove the schedule with `python3 scripts/manage_weekly_backup.py uninstall`. Existing backups are retained when the schedule is removed.

The LaunchAgent runs only while this macOS user account is available. If the Mac is routinely switched off or the staff member changes, migrate the same script to a University-managed scheduled service.

## Local development and checks

Serve the folder through any static HTTP server; ES modules do not run reliably from a `file://` address.

```sh
python3 -m http.server 4173
```

Then open `http://localhost:4173` from this directory. Run the configuration tests with:

```sh
npm test
```

Before deployment, test portrait and landscape layouts, 200% browser zoom, keyboard navigation, VoiceOver, online/offline status, every destination, camera permission, checkout, check-in and the route back to the homepage.
