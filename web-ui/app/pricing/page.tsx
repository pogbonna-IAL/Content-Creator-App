"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { API_URL, getApiUrl } from "@/lib/env";

// Force dynamic rendering (no static generation) to prevent React Context errors
export const dynamic = 'force-dynamic'

interface Tier {
  name: string;
  displayName: string;
  features: string[];
  limits: {
    blog: string;
    social: string;
    audio: string;
    video: string;
  };
}

export default function PricingPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [tiers, setTiers] = useState<Tier[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPlan, setSelectedPlan] = useState<string>("");
  const [selectedProvider, setSelectedProvider] = useState<string>("stripe");

  useEffect(() => {
    fetchTiers();
  }, []);

  const fetchTiers = async () => {
    try {
      const response = await fetch(getApiUrl('api/subscription/tiers'));
      if (response.ok) {
        const data = await response.json();
        setTiers(data.tiers || []);
      }
    } catch (error) {
      console.error("Failed to fetch tiers:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (plan: string) => {
    if (!user) {
      router.push("/auth");
      return;
    }

    try {
      const response = await fetch(getApiUrl('v1/billing/upgrade'), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          plan,
          provider: selectedProvider,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        
        if (data.requires_verification) {
          // Bank transfer - redirect to billing page with instructions
          router.push(`/app/billing?subscription_id=${data.subscription.id}&provider=bank_transfer`);
        } else {
          // Stripe/Paystack - redirect to billing page
          router.push(`/app/billing?subscription_id=${data.subscription.id}&provider=${selectedProvider}`);
        }
      } else {
        const error = await response.json();
        alert(`Failed to upgrade: ${error.detail || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Upgrade failed:", error);
      alert("Failed to upgrade subscription");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading pricing...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Choose Your Plan</h1>
          <p className="text-xl text-gray-600">
            Select the plan that best fits your content creation needs
          </p>
        </div>

        {/* Payment Provider Selection */}
        <div className="mb-8 flex justify-center">
          <div className="bg-white p-4 rounded-lg shadow">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Payment Method
            </label>
            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="stripe">Stripe (Credit Card)</option>
              <option value="paystack">Paystack</option>
              <option value="bank_transfer">Bank Transfer</option>
            </select>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {tiers.map((tier) => (
            <div
              key={tier.name}
              className={`bg-white rounded-lg shadow-lg p-8 ${
                tier.name === "pro" ? "ring-2 ring-blue-500 scale-105" : ""
              }`}
            >
              <h3 className="text-2xl font-bold text-gray-900 mb-2">
                {tier.displayName}
              </h3>
              
              <div className="mb-6">
                <div className="text-sm text-gray-600 mb-2">Monthly Limits:</div>
                <ul className="space-y-1 text-sm">
                  <li>Blog: {tier.limits.blog}</li>
                  <li>Social: {tier.limits.social}</li>
                  <li>Audio: {tier.limits.audio}</li>
                  <li>Video: {tier.limits.video}</li>
                </ul>
              </div>

              <div className="mb-6">
                <div className="text-sm font-medium text-gray-700 mb-2">Features:</div>
                <ul className="space-y-2">
                  {tier.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start">
                      <svg
                        className="h-5 w-5 text-green-500 mr-2"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      <span className="text-sm text-gray-600">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <button
                onClick={() => handleUpgrade(tier.name)}
                disabled={tier.name === "free"}
                className={`w-full py-3 px-4 rounded-md font-medium ${
                  tier.name === "free"
                    ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                    : tier.name === "pro"
                    ? "bg-blue-600 text-white hover:bg-blue-700"
                    : "bg-gray-900 text-white hover:bg-gray-800"
                }`}
              >
                {tier.name === "free" ? "Current Plan" : "Upgrade"}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

