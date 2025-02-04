import matplotlib.pyplot as plt
from matplotlib.widgets import Button, TextBox
import numpy as np

class ECGPeakEditor:
    def __init__(self, signal, r_peaks, sampling_rate):
        self.signal = signal
        self.r_peaks = r_peaks.copy()
        self.sampling_rate = sampling_rate
        self.total_duration = len(signal) / sampling_rate
        
        # Create main figure and subplots
        self.fig = plt.figure(figsize=(15, 10))
        self.fig.subplots_adjust(bottom=0.2)  # Make room for controls
        
        # Create main plot and navigation plot
        self.ax_main = self.fig.add_subplot(211)  # Main ECG view
        self.ax_nav = self.fig.add_subplot(212)   # Navigation view
        
        # Initial window settings
        self.window_size = 20  # seconds
        self.current_position = 0
        
        # Setup the interface
        self.setup_plots()
        self.setup_controls()
        
        # Connect events
        self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        
        plt.show()

    def setup_plots(self):
        # Setup main plot
        self.time = np.arange(len(self.signal)) / self.sampling_rate
        self.line_main, = self.ax_main.plot([], [])
        self.peaks_scatter_main = self.ax_main.scatter([], [], color='red', s=100)
        
        # Setup navigation plot (shows full signal)
        self.ax_nav.plot(self.time, self.signal, alpha=0.5)
        self.peaks_scatter_nav = self.ax_nav.scatter(
            self.r_peaks / self.sampling_rate,
            self.signal[self.r_peaks],
            color='red', s=20, alpha=0.5
        )
        
        # Add window indicator in navigation plot
        self.window_patch = plt.Rectangle((0, 0), 0, 0, facecolor='gray', alpha=0.3)
        self.ax_nav.add_patch(self.window_patch)
        
        # Setup axes
        self.ax_main.grid(True)
        self.ax_nav.grid(True)
        self.ax_main.set_title('ECG Peak Editor (Left click: Add peak, Right click: Remove peak)')
        self.update_view()

    def setup_controls(self):
        # Add navigation buttons
        ax_prev = plt.axes([0.05, 0.05, 0.1, 0.04])
        ax_next = plt.axes([0.16, 0.05, 0.1, 0.04])
        self.btn_prev = Button(ax_prev, 'Previous')
        self.btn_next = Button(ax_next, 'Next')
        self.btn_prev.on_clicked(self.previous_window)
        self.btn_next.on_clicked(self.next_window)
        
        # Add window size control
        ax_window = plt.axes([0.32, 0.05, 0.15, 0.04])
        self.txt_window = TextBox(ax_window, 'Window (s): ', initial=str(self.window_size))
        self.txt_window.on_submit(self.update_window_size)
        
        # Add jump to time control
        ax_jump = plt.axes([0.53, 0.05, 0.15, 0.04])
        self.txt_jump = TextBox(ax_jump, 'Jump to (s): ', initial='0')
        self.txt_jump.on_submit(self.jump_to_time)
        
        # Add save button
        ax_save = plt.axes([0.74, 0.05, 0.1, 0.04])
        self.btn_save = Button(ax_save, 'Save')
        self.btn_save.on_clicked(self.save_peaks)

    def jump_to_time(self, text):
        try:
            jump_time = float(text)
            if 0 <= jump_time <= (self.total_duration - self.window_size):
                self.current_position = jump_time
                self.update_view()
                print(f"Jumped to {jump_time} seconds")
            else:
                print("Time out of range")
        except ValueError:
            print("Invalid time value")

    def update_view(self):
    # Update main plot
        start_idx = int(self.current_position * self.sampling_rate)
        end_idx = int((self.current_position + self.window_size) * self.sampling_rate)
        
        self.line_main.set_data(
            self.time[start_idx:end_idx],
            self.signal[start_idx:end_idx]
        )
        
        # Update peaks in main view
        peaks_in_view = self.r_peaks[
            (self.r_peaks >= start_idx) & 
            (self.r_peaks < end_idx)
        ]
        self.peaks_scatter_main.set_offsets(
            np.c_[peaks_in_view / self.sampling_rate,
                self.signal[peaks_in_view]]
        )
        
        # Update window patch in navigation plot
        self.window_patch.set_bounds(
            self.current_position,
            self.ax_nav.get_ylim()[0],
            self.window_size,
            self.ax_nav.get_ylim()[1] - self.ax_nav.get_ylim()[0]
        )
        
        # Update main plot limits
        self.ax_main.set_xlim(self.current_position, 
                            self.current_position + self.window_size)
        self.ax_main.set_ylim(np.min(self.signal[start_idx:end_idx]) * 1.1,
                            np.max(self.signal[start_idx:end_idx]) * 1.1)
        
        # Update current time display (only if it exists)
        if hasattr(self, 'txt_current_time'):
            self.txt_current_time.set_val(f"{self.current_position:.1f}")
        
        self.fig.canvas.draw_idle()

    def onclick(self, event):
        if event.inaxes == self.ax_main:
            x = event.xdata
            y = event.ydata
            
            # Convert click time to sample index
            clicked_sample = int(round(x * self.sampling_rate))
            
            if event.button == 1:  # Left click to add peak
                # Find local maximum within a window
                window_size = int(0.05 * self.sampling_rate)  # 100ms window
                window_start = max(0, clicked_sample - window_size)
                window_end = min(len(self.signal), clicked_sample + window_size)
                window_data = self.signal[window_start:window_end]
                local_max_idx = window_start + np.argmax(window_data)
                
                self.r_peaks = np.append(self.r_peaks, local_max_idx)
                self.r_peaks.sort()
                print(f"Added peak at {local_max_idx/self.sampling_rate:.2f} seconds")
                
            elif event.button == 3:  # Right click to remove peak
                # Find nearest peak within 100ms
                nearby_peaks = self.r_peaks[
                    (self.r_peaks >= (clicked_sample - 0.1 * self.sampling_rate)) &
                    (self.r_peaks <= (clicked_sample + 0.1 * self.sampling_rate))
                ]
                
                if len(nearby_peaks) > 0:
                    peak_to_remove = nearby_peaks[np.argmin(np.abs(nearby_peaks - clicked_sample))]
                    self.r_peaks = self.r_peaks[self.r_peaks != peak_to_remove]
                    print(f"Removed peak at {peak_to_remove/self.sampling_rate:.2f} seconds")
            
            # Update both plots
            self.peaks_scatter_nav.set_offsets(
                np.c_[self.r_peaks / self.sampling_rate,
                     self.signal[self.r_peaks]]
            )
            self.update_view()

    def previous_window(self, event):
        self.current_position = max(0, self.current_position - self.window_size)
        self.update_view()

    def next_window(self, event):
        self.current_position = min(
            self.total_duration - self.window_size,
            self.current_position + self.window_size
        )
        self.update_view()

    def update_window_size(self, text):
        try:
            new_size = float(text)
            if 1 <= new_size <= self.total_duration:
                self.window_size = new_size
                self.update_view()
        except ValueError:
            pass

    def save_peaks(self, event):
        # Get current timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save with timestamp
        filename = f'r_peaks_edited_{timestamp}.npy'
        filepath='r_peaks/'+filename
        np.save(filepath, self.r_peaks)
        
        # Also save as latest version
        np.save('r_peaks/r_peaks_edited_latest.npy', self.r_peaks)
        
        print(f"Peaks saved to '{filename}' and 'r_peaks_edited_latest.npy'")

    def get_peaks(self):
        return self.r_peaks