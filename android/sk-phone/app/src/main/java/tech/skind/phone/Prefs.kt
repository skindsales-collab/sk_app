package tech.skind.phone

import android.content.Context

/** What the phone remembers: the server, its token (never the PIN), the mode and the last call sent. */
class Prefs(context: Context) {
	private val p = context.getSharedPreferences("sk_phone", Context.MODE_PRIVATE)

	var server: String
		get() = p.getString("server", DEFAULT_SERVER) ?: DEFAULT_SERVER
		set(v) = p.edit().putString("server", v).apply()
	var token: String?
		get() = p.getString("token", null)
		set(v) = p.edit().putString("token", v).apply()
	var name: String
		get() = p.getString("name", "") ?: ""
		set(v) = p.edit().putString("name", v).apply()
	var mode: String
		get() = p.getString("mode", "company") ?: "company"
		set(v) = p.edit().putString("mode", v).apply()
	var lastCall: Long
		get() = p.getLong("last_call", 0L)
		set(v) = p.edit().putLong("last_call", v).apply()
	var lastResult: String
		get() = p.getString("last_result", "") ?: ""
		set(v) = p.edit().putString("last_result", v).apply()

	companion object {
		const val DEFAULT_SERVER = "https://sk-dev.nvi.frappe.cloud"
	}
}
