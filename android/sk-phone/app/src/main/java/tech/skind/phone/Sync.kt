package tech.skind.phone

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.provider.CallLog
import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** Reads the calls since the last one sent and sends them to ERPNext. */
object Sync {
	private const val FIRST_DAYS = 2L
	private const val MAX_CALLS = 500

	fun digits10(number: String?): String {
		val d = (number ?: "").filter { it.isDigit() }
		return if (d.length >= 10) d.takeLast(10) else ""
	}

	fun sha256(text: String): String =
		MessageDigest.getInstance("SHA-256").digest(text.toByteArray()).joinToString("") { "%02x".format(it) }

	@Synchronized
	fun run(context: Context): String {
		val prefs = Prefs(context)
		val token = prefs.token ?: return "Not linked yet"
		if (context.checkSelfPermission(Manifest.permission.READ_CALL_LOG) != PackageManager.PERMISSION_GRANTED) {
			return "Call list permission not given"
		}
		// personal phone: only numbers already in CRM leave the phone
		val business: Set<String>? = if (prefs.mode == "personal") {
			val arr = Api.post(prefs.server, "phone_numbers", mapOf("token" to token)).getJSONObject("message").getJSONArray("hashes")
			(0 until arr.length()).map { arr.getString(it) }.toSet()
		} else {
			null
		}
		val since = if (prefs.lastCall > 0) prefs.lastCall else System.currentTimeMillis() - FIRST_DAYS * 24 * 3600 * 1000
		val calls = JSONArray()
		var newest = since
		val columns = arrayOf(CallLog.Calls._ID, CallLog.Calls.NUMBER, CallLog.Calls.TYPE, CallLog.Calls.DATE, CallLog.Calls.DURATION)
		context.contentResolver.query(CallLog.Calls.CONTENT_URI, columns, "${CallLog.Calls.DATE} > ?", arrayOf(since.toString()),
			"${CallLog.Calls.DATE} ASC")?.use { c ->
			while (c.moveToNext() && calls.length() < MAX_CALLS) {
				val date = c.getLong(3)
				newest = maxOf(newest, date)
				val number = digits10(c.getString(1))
				if (number.isEmpty()) continue
				if (business != null && sha256(number) !in business) continue
				val type = when (c.getInt(2)) {
					CallLog.Calls.OUTGOING_TYPE -> "out"
					CallLog.Calls.INCOMING_TYPE -> "in"
					else -> "missed"
				}
				calls.put(JSONObject().put("id", c.getLong(0)).put("number", number).put("type", type)
					.put("start", date).put("duration", c.getLong(4)))
			}
		}
		var result = "No new calls"
		if (calls.length() > 0) {
			val r = Api.post(prefs.server, "phone_calls", mapOf("token" to token, "calls" to calls.toString())).getJSONObject("message")
			result = "${r.optInt("saved")} calls sent"
		}
		prefs.lastCall = newest
		val at = SimpleDateFormat("dd MMM HH:mm", Locale.getDefault()).format(Date())
		prefs.lastResult = "$at: $result"
		return prefs.lastResult
	}
}
