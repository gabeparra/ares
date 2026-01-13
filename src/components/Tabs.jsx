import React from "react";
import { useNavigate } from "react-router-dom";

function Tabs({ tabs, activeTab, onTabChange, children }) {
  const navigate = useNavigate();

  const handleTabClick = (tabId) => {
    onTabChange(tabId);
    navigate(`/${tabId}`);
  };

  return (
    <div className="glass-tabs flex flex-col flex-1 min-h-0 h-full overflow-hidden rounded-2xl box-border shadow-glass">
      {/* Tab Navigation */}
      <div className="flex gap-2px border-b border-white-opacity-12 pt-4px pb-0 px-4px bg-gradient-to-br from-[rgba(26,26,31,0.98)] to-[rgba(20,20,25,0.98)] overflow-x-auto flex-shrink-0 rounded-t-2xl backdrop-blur-12px">
        <div className="flex gap-2px py-2px px-2px">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`group relative flex items-center gap-6px px-14px py-10px cursor-pointer font-medium text-0.85em transition-all duration-250 whitespace-nowrap flex-shrink-0 rounded-lg border-0 outline-none ${
                activeTab === tab.id
                  ? "text-white bg-gradient-to-br from-[rgba(255,0,0,0.25)] to-[rgba(255,0,0,0.15)] shadow-[0_2px_12px_rgba(255,0,0,0.25),inset_0_1px_0_rgba(255,255,255,0.1)]"
                  : "text-[rgba(255,255,255,0.55)] bg-transparent hover:text-[rgba(255,255,255,0.9)] hover:bg-[rgba(255,255,255,0.06)]"
              }`}
              onClick={() => handleTabClick(tab.id)}
            >
              {/* Active indicator */}
              {activeTab === tab.id && (
                <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-gradient-to-r from-transparent via-[rgba(255,100,100,0.8)] to-transparent rounded-full" />
              )}
              
              {tab.icon && (
                <span className={`text-1em flex-shrink-0 transition-all duration-250 ${
                  activeTab === tab.id 
                    ? "scale-110 filter drop-shadow-[0_0_8px_rgba(255,100,100,0.5)]" 
                    : "opacity-70 group-hover:opacity-100 group-hover:scale-105"
                }`}>
                  {tab.icon}
                </span>
              )}
              <span className={`font-medium transition-all duration-250 hidden sm:inline ${
                activeTab === tab.id ? "font-semibold" : ""
              }`}>
                {tab.label}
              </span>
              {tab.badge && (
                <span className="bg-gradient-to-br from-red-500 to-red-600 text-white px-6px py-2px rounded-md text-0.7em font-bold min-w-16px text-center flex-shrink-0 shadow-md animate-pulse-2">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>
      
      {/* Tab Content */}
      <div className="flex flex-col flex-1 min-h-0 overflow-hidden p-0 rounded-b-2xl box-border bg-[rgba(10,10,15,0.5)]">
        {children}
      </div>
    </div>
  );
}

export default Tabs;
