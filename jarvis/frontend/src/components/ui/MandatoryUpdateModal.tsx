import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, ArrowRight, Download, RefreshCw, XCircle, ShieldAlert, Zap } from 'lucide-react';
import { useUpdateStore } from '../../store/updateStore';
import { UpdateService, getClientPlatform } from '../../services/UpdateService';

export function MandatoryUpdateModal() {
  const platform = getClientPlatform();
  const fileExt = platform === 'android' ? '.apk' : platform === 'ios' ? '.ipa' : '.exe';
  const {
    updateAvailable,
    mandatory,
    currentVersion,
    latestVersion,
    title,
    releaseNotes,
    downloadUrl,
    isUpdating,
    updateStatusText,
    isChecking,
    error,
  } = useUpdateStore();

  if (!updateAvailable || !mandatory) {
    return null;
  }

  const handleUpdate = () => {
    UpdateService.startUpdateInstallation();
  };

  const handleInstantSync = () => {
    UpdateService.syncLiveFrontend();
  };

  const handleManualDownload = () => {
    if (downloadUrl) {
      window.open(downloadUrl, '_blank');
    }
  };

  const handleRecheck = () => {
    UpdateService.checkForUpdates(false);
  };

  const handleExit = () => {
    UpdateService.quitApplication();
  };

  return (
    <AnimatePresence>
      <div
        className="fixed inset-0 z-[99999] flex items-center justify-center bg-[#020408]/90 backdrop-blur-2xl p-4 select-none"
        style={{ pointerEvents: 'auto' }}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.92, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
          className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-red-500/30 bg-[#0a0f1d]/95 p-6 shadow-[0_0_50px_rgba(239,68,68,0.25)] sm:p-8"
        >
          {/* Ambient Cyber Light Effect */}
          <div className="pointer-events-none absolute -left-20 -top-20 h-56 w-56 rounded-full bg-red-600/15 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-20 -right-20 h-56 w-56 rounded-full bg-cyan-600/15 blur-3xl" />

          {/* Header */}
          <div className="relative flex items-center gap-4 border-b border-white/10 pb-5">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-red-500/40 bg-red-500/10 shadow-[0_0_20px_rgba(239,68,68,0.3)]">
              <ShieldAlert className="h-6 w-6 text-red-400 animate-pulse" />
            </div>
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-red-500/40 bg-red-500/10 px-2.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-red-400">
                <AlertTriangle className="h-3 w-3" /> Mandatory Update Required
              </div>
              <h2 className="mt-1 text-xl font-bold tracking-tight text-white font-sans">
                {title || 'New Jarvis Version Required'}
              </h2>
            </div>
          </div>

          {/* Body Content */}
          <div className="relative mt-5 space-y-4 text-sm text-zinc-300">
            <p className="text-zinc-300 leading-relaxed">
              A newer frontend and core version of <span className="font-semibold text-white">Jarvis OS</span> has been deployed.
              To maintain system stability, security, and protocol compatibility, you must update before using the application.
            </p>

            {/* Version Diff Banner */}
            <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <div className="flex flex-col">
                <span className="text-[11px] font-mono uppercase text-zinc-400">Current Installed</span>
                <span className="font-mono text-base font-medium text-zinc-300">v{currentVersion}</span>
              </div>
              <ArrowRight className="h-5 w-5 text-zinc-500" />
              <div className="flex flex-col items-end">
                <span className="text-[11px] font-mono uppercase text-cyan-400 font-semibold">Latest Required</span>
                <span className="font-mono text-base font-bold text-cyan-400 drop-shadow-[0_0_8px_rgba(6,182,212,0.4)]">
                  v{latestVersion}
                </span>
              </div>
            </div>

            {/* Release Notes */}
            {releaseNotes && (
              <div className="rounded-xl border border-white/10 bg-black/40 p-3.5">
                <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1.5">
                  Update Highlights
                </div>
                <div className="max-h-28 overflow-y-auto text-xs text-zinc-400 whitespace-pre-wrap font-mono leading-relaxed">
                  {releaseNotes}
                </div>
              </div>
            )}

            {/* Live Update Status Banner */}
            {updateStatusText && (
              <div className="flex items-center gap-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs text-cyan-300">
                <RefreshCw className="h-4 w-4 animate-spin shrink-0 text-cyan-400" />
                <span>{updateStatusText}</span>
              </div>
            )}

            {error && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                {error}
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="relative mt-6 flex flex-col gap-2.5 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={handleExit}
              className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-xs font-medium text-zinc-400 hover:bg-white/10 hover:text-white transition-all cursor-pointer"
            >
              <XCircle className="h-4 w-4" /> Exit Jarvis
            </button>

            <button
              type="button"
              onClick={handleRecheck}
              disabled={isChecking}
              className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-xs font-medium text-zinc-300 hover:bg-white/10 hover:text-white transition-all cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${isChecking ? 'animate-spin' : ''}`} /> Re-check
            </button>

            <button
              type="button"
              onClick={handleManualDownload}
              className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-4 py-2.5 text-xs font-medium text-cyan-300 hover:bg-cyan-500/20 hover:text-cyan-200 transition-all cursor-pointer"
            >
              <Download className="h-4 w-4" /> Download {fileExt}
            </button>

            <button
              type="button"
              onClick={handleInstantSync}
              disabled={isUpdating}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 px-5 py-2.5 text-xs font-semibold text-white shadow-[0_0_20px_rgba(16,185,129,0.4)] hover:brightness-110 active:scale-[0.98] transition-all cursor-pointer disabled:opacity-60"
            >
              <Zap className="h-4 w-4 text-yellow-300 animate-pulse" /> Instant Sync (No Reinstall)
            </button>

            <button
              type="button"
              onClick={handleUpdate}
              disabled={isUpdating}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-white/10 border border-white/10 px-4 py-2.5 text-xs font-medium text-zinc-300 hover:bg-white/15 hover:text-white transition-all cursor-pointer disabled:opacity-60"
            >
              {isUpdating ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" /> Updating...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" /> Download Full Installer
                </>
              )}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

