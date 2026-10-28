package tech.skind.phone

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.ScrollView
import android.widget.TextView

/** One screen: link the phone (mobile + PIN, company or personal phone), then calls go by themselves. */
class MainActivity : Activity() {
	private lateinit var prefs: Prefs
	private lateinit var status: TextView

	override fun onCreate(savedInstanceState: Bundle?) {
		super.onCreate(savedInstanceState)
		prefs = Prefs(this)
		val pad = (16 * resources.displayMetrics.density).toInt()
		val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(pad, pad, pad, pad) }

		fun label(text: String, size: Float = 16f) = TextView(this).apply { this.text = text; textSize = size; setPadding(0, pad / 2, 0, pad / 4) }
		box.addView(label("SK Phone · SK Ind Tech", 22f))
		box.addView(label("Sends your calls (number, time, length) to the SK App, matched to the lead or customer. No recording, no contacts, no messages.\n" +
			"तुमचे कॉल (नंबर, वेळ, कालावधी) SK App मध्ये पाठवते. रेकॉर्डिंग नाही, कॉन्टॅक्ट नाहीत, मेसेज नाहीत.", 14f))

		val server = EditText(this).apply { setText(prefs.server); inputType = InputType.TYPE_TEXT_VARIATION_URI; hint = "Server" }
		val mobile = EditText(this).apply { inputType = InputType.TYPE_CLASS_PHONE; hint = "Mobile number · मोबाईल नंबर" }
		val pin = EditText(this).apply { inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_VARIATION_PASSWORD; hint = "PIN · पिन" }
		val modes = RadioGroup(this)
		val company = RadioButton(this).apply { id = 1; text = "Company phone: all calls · कंपनीचा फोन: सर्व कॉल" }
		val personal = RadioButton(this).apply { id = 2; text = "Personal phone: only customer calls · स्वतःचा फोन: फक्त ग्राहकांचे कॉल" }
		modes.addView(company)
		modes.addView(personal)
		modes.check(if (prefs.mode == "personal") 2 else 1)
		val link = Button(this).apply { text = "Link this phone · फोन जोडा" }
		val sync = Button(this).apply { text = "Send calls now · आता कॉल पाठवा" }
		status = label("", 15f)

		box.addView(label("Server"))
		box.addView(server, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
		box.addView(mobile, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
		box.addView(pin, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
		box.addView(modes)
		box.addView(link)
		box.addView(sync)
		box.addView(status)
		setContentView(ScrollView(this).apply { addView(box) })
		show()

		link.setOnClickListener {
			val mode = if (modes.checkedRadioButtonId == 2) "personal" else "company"
			val url = server.text.toString().trim()
			status.text = "…"
			Thread {
				val msg = try {
					val r = Api.post(url, "phone_link", mapOf("mobile" to mobile.text.toString(), "pin" to pin.text.toString(),
						"device" to "${Build.MANUFACTURER} ${Build.MODEL}", "mode" to mode)).getJSONObject("message")
					prefs.server = url
					prefs.token = r.getString("token")
					prefs.name = r.optString("name")
					prefs.mode = mode
					prefs.lastCall = 0L
					SyncWorker.schedule(this)
					"Linked · जोडला: ${prefs.name}"
				} catch (e: Exception) {
					"Not linked: ${e.message}"
				}
				runOnUiThread { pin.setText(""); status.text = msg; show() }
			}.start()
		}
		sync.setOnClickListener {
			status.text = "…"
			Thread {
				val msg = try { Sync.run(this) } catch (e: Exception) { "Error: ${e.message}" }
				runOnUiThread { status.text = msg; show() }
			}.start()
		}
		if (checkSelfPermission(Manifest.permission.READ_CALL_LOG) != PackageManager.PERMISSION_GRANTED) {
			requestPermissions(arrayOf(Manifest.permission.READ_CALL_LOG), 1)
		}
		if (prefs.token != null) SyncWorker.schedule(this)
	}

	private fun show() {
		val who = if (prefs.token != null) "Linked to ${prefs.name} · ${if (prefs.mode == "personal") "personal phone" else "company phone"}" else "Not linked yet · अजून जोडला नाही"
		status.text = listOf(status.text.toString(), who, prefs.lastResult).filter { it.isNotBlank() && it != "…" }.distinct().joinToString("\n")
	}
}
