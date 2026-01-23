"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { API_URL } from "../lib/env";

// Force dynamic rendering (no static generation)
export const dynamic = 'force-dynamic';

interface Subscription {
  id: number;
  plan: string;
  status: string;
  provider: string;
  current_period_end: string;
}

interface PaymentInstructions {
  account_number: string;
  bank_name: string;
  account_name: string;
  routing_number: string;
  instructions: string;
}

function BillingContent() {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const subscriptionId = searchParams.get("subscription_id");
  const provider = searchParams.get("provider");

  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [paymentInstructions, setPaymentInstructions] = useState<PaymentInstructions | null>(null);
  const [loading, setLoading] = useState(true);
  const [reference, setReference] = useState("");

  useEffect(() => {
    if (!user) {
      router.push("/auth");
      return;
    }
    fetchSubscription();
  }, [user]);

  const fetchSubscription = async () => {
    try {
      const response = await fetch(`${API_URL}/v1/billing/subscription`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setSubscription(data.subscription);
      }
    } catch (error) {
      console.error("Failed to fetch subscription:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleBankTransferRequest = async () => {
    if (!subscription) return;

    try {
      const response = await fetch(`${API_URL}/v1/billing/bank-transfer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          plan: subscription.plan,
          reference: reference || undefined,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setPaymentInstructions(data.payment_instructions);
        setSubscription(data.subscription);
      } else {
        const error = await response.json();
        alert(`Failed to create bank transfer request: ${error.detail || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Bank transfer request failed:", error);
      alert("Failed to create bank transfer request");
    }
  };

  const handleCancel = async () => {
    if (!confirm("Are you sure you want to cancel your subscription?")) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/v1/billing/cancel`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (response.ok) {
        alert("Subscription cancelled successfully");
        fetchSubscription();
      } else {
        const error = await response.json();
        alert(`Failed to cancel subscription: ${error.detail || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Cancel failed:", error);
      alert("Failed to cancel subscription");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading billing information...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Billing & Subscription</h1>

        {subscription ? (
          <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Current Subscription</h2>
            
            <div className="space-y-4">
              <div>
                <span className="text-sm font-medium text-gray-700">Plan:</span>
                <span className="ml-2 text-lg font-semibold capitalize">{subscription.plan}</span>
              </div>
              
              <div>
                <span className="text-sm font-medium text-gray-700">Status:</span>
                <span className={`ml-2 px-2 py-1 rounded text-sm font-medium ${
                  subscription.status === "active"
                    ? "bg-green-100 text-green-800"
                    : subscription.status === "pending_verification"
                    ? "bg-yellow-100 text-yellow-800"
                    : "bg-red-100 text-red-800"
                }`}>
                  {subscription.status}
                </span>
              </div>
              
              <div>
                <span className="text-sm font-medium text-gray-700">Provider:</span>
                <span className="ml-2 capitalize">{subscription.provider || "N/A"}</span>
              </div>
              
              <div>
                <span className="text-sm font-medium text-gray-700">Current Period End:</span>
                <span className="ml-2">
                  {new Date(subscription.current_period_end).toLocaleDateString()}
                </span>
              </div>
            </div>

            {subscription.status === "active" && (
              <button
                onClick={handleCancel}
                className="mt-6 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
              >
                Cancel Subscription
              </button>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
            <p className="text-gray-600">You are currently on the Free plan.</p>
            <button
              onClick={() => router.push("/pricing")}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              View Plans
            </button>
          </div>
        )}

        {/* Bank Transfer Section */}
        {provider === "bank_transfer" && (
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Bank Transfer Payment</h2>
            
            {paymentInstructions ? (
              <div className="space-y-4">
                <div className="bg-gray-50 p-4 rounded-md">
                  <h3 className="font-medium text-gray-900 mb-2">Payment Instructions</h3>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-medium">Account Number:</span>{" "}
                      {paymentInstructions.account_number}
                    </div>
                    <div>
                      <span className="font-medium">Bank Name:</span>{" "}
                      {paymentInstructions.bank_name}
                    </div>
                    <div>
                      <span className="font-medium">Account Name:</span>{" "}
                      {paymentInstructions.account_name}
                    </div>
                    {paymentInstructions.routing_number && (
                      <div>
                        <span className="font-medium">Routing Number:</span>{" "}
                        {paymentInstructions.routing_number}
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="bg-blue-50 p-4 rounded-md">
                  <p className="text-sm text-blue-900">
                    {paymentInstructions.instructions}
                  </p>
                </div>
                
                <div className="text-sm text-gray-600">
                  <p>
                    After completing the transfer, your subscription will be activated once we verify the payment.
                    This usually takes 1-2 business days.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Payment Reference (Optional)
                  </label>
                  <input
                    type="text"
                    value={reference}
                    onChange={(e) => setReference(e.target.value)}
                    placeholder="Enter payment reference if available"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <button
                  onClick={handleBankTransferRequest}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Get Payment Instructions
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function BillingPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading billing information...</div>
      </div>
    }>
      <BillingContent />
    </Suspense>
  );
}

