import { create } from 'zustand';

export interface UpdateState {
  isChecking: boolean;
  updateAvailable: boolean;
  mandatory: boolean;
  currentVersion: string;
  latestVersion: string;
  title: string;
  releaseNotes: string;
  downloadUrl: string;
  publishedAt: string | null;
  isUpdating: boolean;
  updateStatusText: string | null;
  error: string | null;
  lastChecked: number | null;

  setUpdateInfo: (info: Partial<UpdateState>) => void;
  setIsUpdating: (val: boolean) => void;
  setUpdateStatusText: (text: string | null) => void;
  setError: (err: string | null) => void;
  reset: () => void;
}

export const useUpdateStore = create<UpdateState>((set) => ({
  isChecking: false,
  updateAvailable: false,
  mandatory: false,
  currentVersion: '1.0.0',
  latestVersion: '1.0.0',
  title: '',
  releaseNotes: '',
  downloadUrl: '',
  publishedAt: null,
  isUpdating: false,
  updateStatusText: null,
  error: null,
  lastChecked: null,

  setUpdateInfo: (info) => set((state) => ({ ...state, ...info })),
  setIsUpdating: (val) => set({ isUpdating: val }),
  setUpdateStatusText: (text) => set({ updateStatusText: text }),
  setError: (err) => set({ error: err }),
  reset: () =>
    set({
      updateAvailable: false,
      mandatory: false,
      isUpdating: false,
      updateStatusText: null,
      error: null,
    }),
}));

