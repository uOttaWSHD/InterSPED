// hello_vitals.cpp
// SmartSpectra Hello Vitals - Minimal Example

#include <smartspectra/container/foreground_container.hpp>
#include <smartspectra/container/settings.hpp>
#include <smartspectra/gui/opencv_hud.hpp>
#include <physiology/modules/messages/metrics.h>
#include <physiology/modules/messages/status.h>
#include <glog/logging.h>
#include <opencv2/opencv.hpp>
#include <cstdlib>
#include <fstream>
#include <iostream>

using namespace presage::smartspectra;

int main(int argc, char** argv) {
    // Initialize logging
    google::InitGoogleLogging(argv[0]);
    FLAGS_alsologtostderr = true;
    
    // Get API key
    std::string api_key;
    std::string api_key_source;
    if (argc > 1) {
        api_key = argv[1];
        api_key_source = "argv[1]";
    } else if (const char* env_key = std::getenv("SMARTSPECTRA_API_KEY")) {
        api_key = env_key;
        api_key_source = "SMARTSPECTRA_API_KEY";
    } else {
        std::cout << "Usage: ./hello_vitals YOUR_API_KEY\n";
        std::cout << "Or set SMARTSPECTRA_API_KEY environment variable\n";
        std::cout << "Get your API key from: https://physiology.presagetech.com\n";
        return 1;
    }

    if (api_key.empty()) {
        std::cout << "API key is empty. Pass it as argv[1] or set SMARTSPECTRA_API_KEY.\n";
        return 1;
    }
    std::cout << "Using API key from " << api_key_source << " (length=" << api_key.size() << ")\n";
    
    std::cout << "Starting SmartSpectra Hello Vitals...\n";
    
    try {
        // Resolve video source: prefer explicit input path, else device index
        int device_index = 0;
        if (const char* env_dev = std::getenv("SMARTSPECTRA_CAMERA_INDEX")) {
            try {
                device_index = std::stoi(std::string(env_dev));
            } catch (...) {
                std::cerr << "SMARTSPECTRA_CAMERA_INDEX is not a valid integer; defaulting to 0\n";
                device_index = 0;
            }
        }
        std::string input_video_path;
        if (const char* env_input = std::getenv("SMARTSPECTRA_INPUT_VIDEO")) {
            input_video_path = env_input;
        }

        int capture_width = 640;
        if (const char* w = std::getenv("SMARTSPECTRA_WIDTH")) capture_width = std::stoi(w);
        
        int capture_height = 480;
        if (const char* h = std::getenv("SMARTSPECTRA_HEIGHT")) capture_height = std::stoi(h);

        // Create settings
        container::settings::Settings<
            container::settings::OperationMode::Continuous,
            container::settings::IntegrationMode::Rest
        > settings;

        // Configure camera or input path
        settings.video_source.device_index = device_index;
        settings.video_source.capture_width_px = capture_width;
        settings.video_source.capture_height_px = capture_height;
        settings.video_source.codec = presage::camera::CaptureCodec::MJPG;
        settings.video_source.auto_lock = true;
        settings.video_source.input_video_path = input_video_path;
        settings.video_source.input_video_time_path = "";
        
        // Basic settings
        bool headless = false;
        if (const char* env_headless = std::getenv("SMARTSPECTRA_HEADLESS")) {
            headless = (std::string(env_headless) == "1" || std::string(env_headless) == "true");
        }
        settings.headless = headless;
        settings.enable_edge_metrics = true;
        settings.verbosity_level = 1;
        
        // Continuous mode buffer
        settings.continuous.preprocessed_data_buffer_duration_s = 0.5;
        
        // API key for REST
        settings.integration.api_key = api_key;
        
        // Create container
        auto container = std::make_unique<container::CpuContinuousRestForegroundContainer>(settings);
        
        // HUD size - must fit within video dimensions, use smaller values for portrait videos
        int hud_width = std::min(capture_width - 20, 400);
        int hud_height = std::min(capture_height / 2, 200);
        auto hud = std::make_unique<gui::OpenCvHud>(10, 0, hud_width, hud_height);
        
        std::cout << "Using device_index=" << settings.video_source.device_index
                  << (input_video_path.empty() ? "" : std::string(" input_video_path=") + input_video_path) << "\n";

        if (!input_video_path.empty()) {
            // Check if file exists before passing to SDK
            std::ifstream file_check(input_video_path);
            if (!file_check.good()) {
                std::cerr << "ERROR: Input video file not found: " << input_video_path << "\n";
                std::cerr << "Make sure the file exists and the path is correct.\n";
                return 1;
            }
            std::cout << "✓ Video file found at: " << input_video_path << "\n";
        }
        
        // Set up callbacks
        auto status = container->SetOnCoreMetricsOutput(
            [](const presage::physiology::MetricsBuffer& metrics, int64_t timestamp) {
                float pulse = 0;
                float breathing = 0;
                if (!metrics.pulse().rate().empty()){
                    pulse = metrics.pulse().rate().rbegin()->value();
                }
                if (!metrics.breathing().rate().empty()){
                    breathing = metrics.breathing().rate().rbegin()->value();
                }
                
                if (!metrics.pulse().rate().empty() && !metrics.breathing().rate().empty()){
                    std::cout << "Vitals - Pulse: " << pulse << " BPM, Breathing: " << breathing << " BPM\n";
                }
                return absl::OkStatus();
            }
        ); 
        if (!status.ok()) {
            std::cerr << "Failed to set metrics callback: " << status.message() << "\n";
            return 1;
        }
        
        status = container->SetOnVideoOutput(
            [headless](cv::Mat& frame, int64_t timestamp) {
                if (!headless) {
                    cv::imshow("SmartSpectra Hello Vitals", frame);
                    char key = cv::waitKey(1) & 0xFF;
                    if (key == 'q' || key == 27) {
                        return absl::CancelledError("User quit");
                    }
                }
                return absl::OkStatus();
            }
        ); 
        if (!status.ok()) {
            std::cerr << "Failed to set video callback: " << status.message() << "\n";
            return 1;
        }
        
        status = container->SetOnStatusChange(
            [](presage::physiology::StatusValue imaging_status) {
                std::cout << "Imaging/processing status: " << presage::physiology::GetStatusDescription(imaging_status.value()) << "\n";
                return absl::OkStatus();
            }
        ); 
        if(!status.ok()) {
            std::cerr << "Failed to set status callback: " << status.message() << "\n";
            return 1;
        }
        
        // Initialize and run
        std::cout << "Initializing camera and processing...\n";
        if (auto status = container->Initialize(); !status.ok()) {
            std::cerr << "Failed to initialize: " << status.message() << "\n";
            return 1;
        }
        
        std::cout << "Ready! Press 's' to start/stop recording data.\nPress 'q' to quit.\n";
        if (auto status = container->Run(); !status.ok()) {
            std::cerr << "Processing failed: " << status.message() << "\n";
            return 1;
        }
        
        cv::destroyAllWindows();
        std::cout << "Done!\n";
        return 0;
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
}
