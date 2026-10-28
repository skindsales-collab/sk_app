package tech.skind.phone

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit

/** Sends new calls every 15 minutes when there is internet (Android's shortest repeat). */
class SyncWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
	override fun doWork(): Result = try {
		Sync.run(applicationContext)
		Result.success()
	} catch (e: ApiError) {
		Prefs(applicationContext).lastResult = "Error: ${e.message}"
		Result.success()
	} catch (e: Exception) {
		Result.retry()
	}

	companion object {
		fun schedule(context: Context) {
			val request = PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES)
				.setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
				.build()
			WorkManager.getInstance(context).enqueueUniquePeriodicWork("sk-phone-sync", ExistingPeriodicWorkPolicy.KEEP, request)
		}
	}
}
