/*
hello_vitals.cpp
Author: Dan Shan
Date: Jan 17, 2026

Description:
Set a pathway to a video file of someone's face to extract and display vitals

** DONT FORGET TO REBUILD THE PROJECT AFTER UPDATING THIS FILE **

rm -rf build
cmake -S . -B build
cmake --build build --config Release
cmake --build build --config Debug
cmake --build build
./build/hello_vitals
*/

#include <smartspectra/container/foreground_container.hpp>
#include <smartspectra/container/settings.hpp>
#include <smartspectra/gui/opencv_hud.hpp>
#include <physiology/modules/messages/metrics.h>
#include <physiology/modules/messages/status.h>
#include <glog/logging.h>
#include <opencv2/opencv.hpp>
#include <iostream>
#include "dotenv.h"
#include <nlohmann/json.hpp>
#include <fstream>

using namespace presage::smartspectra;

int main(int argc, char** argv) {
    // Initialize logging
    google::InitGoogleLogging(argv[0]);
    FLAGS_alsologtostderr = true;

    // Get API key
    std::string api_key;
    if (argc > 1) {
        api_key = argv[1];
    } else api_key = SMARTSPECTRA_API_KEY;
    std::cout << "Starting SmartSpectra Hello Vitals...\n";

    // Load input JSON
    std::ifstream input_file("data/input.json");
    nlohmann::json input_json;
    input_file >> input_json;
    std::string video_path = input_json["video_path"];

    // Clear past output
    nlohmann::json out = {
        {"timestamp", nlohmann::json::array()},
        {"pulse", nlohmann::json::array()},
        {"breathing", nlohmann::json::array()}
    };
    std::ofstream o("data/output.json", std::ofstream::trunc);
    o << std::setw(4) << out << std::endl;
    o.close();

    try {
        // Create settings
        container::settings::Settings<
            container::settings::OperationMode::Continuous,
            container::settings::IntegrationMode::Rest
        > settings;

        // Configure camera (defaults work for most cases)

        // settings.video_source.device_index = 0;
        settings.video_source.device_index = -1;
        settings.video_source.input_video_path = video_path;

        // NOTE: If capture_width and/or capture_height is
        //     modified the HUD will also need to be changed
        settings.video_source.capture_width_px = 1280;
        settings.video_source.capture_height_px = 720;
        settings.video_source.codec = presage::camera::CaptureCodec::MJPG;
        settings.video_source.auto_lock = true;
        // settings.video_source.input_video_path = ""; // paused for testing
        settings.video_source.input_video_time_path = "";

        // Basic settings
        settings.headless = true;
        settings.enable_edge_metrics = true;
        settings.verbosity_level = 1;

        // Continuous mode buffer
        settings.continuous.preprocessed_data_buffer_duration_s = 0.5;

        // API key for REST
        settings.integration.api_key = api_key;

        // Create container
        auto container = std::make_unique<container::CpuContinuousRestForegroundContainer>(settings);
        // auto hud = std::make_unique<gui::OpenCvHud>(
        //     0, 0,
        //     400,   // width = frame width
        //     854    // height = frame height
        // );

        // Set up callbacks
        // NOTE: If code in callbacks adds more than 75ms of delay it might affect
        //       incoming data.

     auto status = container->SetOnCoreMetricsOutput(
    [&out](const presage::physiology::MetricsBuffer& metrics, int64_t timestamp) {
       // REPLACE the ternary push_back blocks with explicit if/else

            out["timestamp"].push_back(timestamp);

            if (!metrics.pulse().rate().empty()) {
                out["pulse"].push_back(metrics.pulse().rate().rbegin()->value());
            } else {
                out["pulse"].push_back(nullptr);
            }

            if (!metrics.breathing().rate().empty()) {
                out["breathing"].push_back(metrics.breathing().rate().rbegin()->value());
            } else {
                out["breathing"].push_back(nullptr);
            }

        return absl::OkStatus();
    }
);
        if (!status.ok()) {
            std::cerr << "Failed to set metrics callback: " << status.message() << "\n";
            return 1;
        }

       
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
        // Write output JSON
        std::ofstream o("data/output.json", std::ofstream::trunc);
        if (o.is_open()) {
            o << std::setw(4) << out << std::endl;
            o.close();
        }

        cv::destroyAllWindows();
        std::cout << "Done!\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
}