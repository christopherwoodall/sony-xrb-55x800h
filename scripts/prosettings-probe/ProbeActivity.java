package com.hermes.prosettingsprobe;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Bundle;
import android.os.IBinder;
import android.util.Log;
import com.sony.dtv.b2b.prosettings.IProSettingsService;
import java.io.FileWriter;

public class ProbeActivity extends Activity {
    private static final String TAG = "PSProbe";

    // PackedPubkey.ENCRYPTED_PUBKEY from NodeRuntimePrivilege (public material)
    private static final String PUBKEY_B64 =
        "YAnzetltAhntN8c9S6Bft0FiXLODyroM7ou2bGEuPLhFikB/Mi9YKX26HML5ssc5t55o/8fh34MaOymXVl3TIz2MM0iBrWcQkJitX7cP3bEV/XeOj/o6GthXqXdTjhwXzDdH89aa3FfirB9ZCSQr4iLuRURA914GIGK5EIwDMqcWfACIQdsYVeV4NhQuSVw5thBiuMMBKUgRJmdcb9LQh2vV12sdib9DYR7IxQa2ALifFBmcAXwITqgBTLCUFQQ1EkLO4XEFv8ZtwcShVsH8vbrWad2cMnE+b0KMwS81Oq/j94t1+vR5yPsePjcOUS0afMRFzsVqUO2jWdOyagMtE25wD4zgGDHcBYXGDn6seAAsjghFVjqRpmc2ZFhyJopCqHV6bq0QZGQGzKXcQD9YL0HP+/aOI7UM9CNSZN9a8VaY7bmjQ0dwctt1598zEAleYLAaj+lDCiEmFaxchKVGaf8EGPzmY8+v6H3ChIzig87aFqASoixDt4RguUXHdD3mJQjYhTSsPQlTrRs0USYoUi4FNo23C5SwYs2UKqCq5MTHe7Ut4uxsHwI3vW/FlxlHNurSMNA6HxNLL94+ZhOi0DwSIpX7gC2e4L39ET9ndwYjuFOXOk7O4uWpn3fl8dPOd6wCb1PEnjOVY1qtmq4J768UT3Twz5HddvYPzkydS4I=";

    private IProSettingsService svc;

    private final ServiceConnection conn = new ServiceConnection() {
        @Override public void onServiceConnected(ComponentName name, IBinder binder) {
            svc = IProSettingsService.Stub.asInterface(binder);
            log("BOUND to ProSettingsService");
            Thread t = new Thread(new Runnable() { @Override public void run() { probe(); }});
            t.start();
        }
        @Override public void onServiceDisconnected(ComponentName name) { svc = null; }
    };

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        Intent i = new Intent();
        i.setComponent(new ComponentName(
            "com.sony.dtv.b2b.prosettings",
            "com.sony.dtv.b2b.prosettings.ProSettingsService"));
        boolean ok = bindService(i, conn, Context.BIND_AUTO_CREATE);
        log("bindService -> " + ok);
    }

    private void log(String s) {
        Log.i(TAG, s);
        try {
            FileWriter f = new FileWriter("/sdcard/psprobe.txt", true);
            f.write(s + "\n");
            f.flush();
            f.close();
        } catch (Exception e) { /* logcat only */ }
    }

    private void call(String what, Runnable0 r) {
        try { log(what + ": " + r.run()); }
        catch (Throwable t) { log(what + " ERR: " + t); }
    }

    private interface Runnable0 { Object run() throws Exception; }

    private void probe() {
        call("decryptPhrase_MasterKey", new Runnable0() { public Object run() throws Exception {
            return svc.decryptPhrase("MasterKey", PUBKEY_B64); }});
        call("decryptPhrase_badkey", new Runnable0() { public Object run() throws Exception {
            return svc.decryptPhrase("NoSuchKey", PUBKEY_B64); }});
        call("getConfiguredWifiNetworks", new Runnable0() { public Object run() throws Exception {
            return svc.getConfiguredWifiNetworks(); }});
        call("getIpControlPSK", new Runnable0() { public Object run() throws Exception {
            return svc.getIpControlPSK(); }});
        call("getDeviceId", new Runnable0() { public Object run() throws Exception {
            return svc.getDeviceId(); }});
        call("getSoftwareVersionDisplay", new Runnable0() { public Object run() throws Exception {
            return svc.getSoftwareVersionDisplay(); }});
        call("getMtkHotelMode", new Runnable0() { public Object run() throws Exception {
            return svc.getMtkHotelMode(); }});
        call("getIpControlAuthentication", new Runnable0() { public Object run() throws Exception {
            return Integer.valueOf(svc.getIpControlAuthentication()); }});
        log("PROBE_DONE");
        runOnUiThread(new Runnable() { @Override public void run() { finish(); }});
    }
}
