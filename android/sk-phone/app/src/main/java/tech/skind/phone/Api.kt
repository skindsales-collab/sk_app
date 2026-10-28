package tech.skind.phone

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

class ApiError(message: String) : Exception(message)

/** Calls the SK App endpoints on ERPNext (form POST, JSON answer). */
object Api {
	fun post(server: String, method: String, form: Map<String, String>): JSONObject {
		val url = URL(server.trim().trimEnd('/') + "/api/method/sk_app.api." + method)
		val body = form.entries.joinToString("&") {
			URLEncoder.encode(it.key, "UTF-8") + "=" + URLEncoder.encode(it.value, "UTF-8")
		}
		val conn = url.openConnection() as HttpURLConnection
		try {
			conn.requestMethod = "POST"
			conn.doOutput = true
			conn.connectTimeout = 20000
			conn.readTimeout = 60000
			conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
			conn.setRequestProperty("Accept", "application/json")
			conn.outputStream.use { it.write(body.toByteArray()) }
			val code = conn.responseCode
			val stream = if (code < 400) conn.inputStream else conn.errorStream
			val text = stream?.bufferedReader()?.use { it.readText() } ?: ""
			val json = try { JSONObject(text) } catch (e: Exception) { JSONObject() }
			if (code >= 400) throw ApiError(serverMessage(json) ?: "Server error $code")
			return json
		} finally {
			conn.disconnect()
		}
	}

	private fun serverMessage(json: JSONObject): String? = try {
		JSONObject(JSONArray(json.getString("_server_messages")).getString(0)).getString("message")
	} catch (e: Exception) {
		null
	}
}
