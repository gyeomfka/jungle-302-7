let temporaryConfirmed = [];

function addToConfirmed(userId) {
  const candidateElement = document.querySelector(
    `#candidate-list [data-user-id="${userId}"]`
  );
  const confirmedList = document.getElementById("confirmed-list");

  if (candidateElement) {
    const userName = candidateElement.querySelector("span").textContent;

    // 임시 확정 목록에 추가
    temporaryConfirmed.push(userId);

    // UI에서 후보자 목록에서 제거
    candidateElement.remove();

    // 확정 목록에 추가
    const confirmedElement = document.createElement("div");
    confirmedElement.className =
      "flex items-center justify-between p-2 bg-gray-50 rounded";
    confirmedElement.setAttribute("data-user-id", userId);
    confirmedElement.innerHTML = `
        <span class="text-sm">${userName}</span>
        <div class="flex space-x-2">
          <button type="button" onclick="showUserProfile('${userId}')" 
                  class="text-xs px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600">
            소개
          </button>
          <button type="button" onclick="removeFromConfirmed('${userId}')" 
                  class="text-xs px-2 py-1 bg-red-500 text-white rounded hover:bg-red-600">
            제거
          </button>
        </div>
      `;
    confirmedList.appendChild(confirmedElement);
  }
}

function removeFromConfirmed(userId) {
  const confirmedElement = document.querySelector(
    `#confirmed-list [data-user-id="${userId}"]`
  );
  const candidateList = document.getElementById("candidate-list");

  if (confirmedElement) {
    const userName = confirmedElement.querySelector("span").textContent;

    // 임시 확정 목록에서 제거
    temporaryConfirmed = temporaryConfirmed.filter((id) => id !== userId);

    // UI에서 확정 목록에서 제거
    confirmedElement.remove();

    // 후보자 목록에 다시 추가
    const candidateElement = document.createElement("div");
    candidateElement.className =
      "flex items-center justify-between p-2 bg-gray-50 rounded";
    candidateElement.setAttribute("data-user-id", userId);
    candidateElement.innerHTML = `
        <span class="text-sm">${userName}</span>
        <div class="flex space-x-2">
          <button type="button" onclick="showUserProfile('${userId}')" 
                  class="text-xs px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600">
            소개
          </button>
          <button type="button" onclick="addToConfirmed('${userId}')" 
                  class="text-xs px-2 py-1 bg-green-500 text-white rounded hover:bg-green-600">
            승인
          </button>
        </div>
      `;
    candidateList.appendChild(candidateElement);
  }
}

async function confirmCandidates(studyId) {
  // 선택된 날짜 확인
  const selectedDate = document.querySelector(
    'input[name="study_date"]:checked'
  );
  if (!selectedDate) {
    alert("스터디 진행 날짜를 선택해주세요.");
    return;
  }

  // 현재 확정 목록의 모든 사용자 ID 수집
  const confirmedElements = document.querySelectorAll(
    "#confirmed-list [data-user-id]"
  );
  const allConfirmedIds = Array.from(confirmedElements).map((el) =>
    el.getAttribute("data-user-id")
  );

  if (allConfirmedIds.length === 0) {
    alert("확정할 참가자가 없습니다.");
    return;
  }

  try {
    const response = await fetch(`/study/${studyId}/confirm-candidates`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({
        confirmed_candidates: allConfirmedIds,
        study_date: selectedDate.value,
      }),
    });

    if (response.ok) {
      alert("참가자가 확정되었습니다!");
      closeDetail();
    } else {
      const errorText = await response.text();
      alert(`확정 실패: ${errorText}`);
    }
  } catch (error) {
    console.error("참가자 확정 오류:", error);
    alert("확정 중 오류가 발생했습니다. 다시 시도해주세요.");
  }
}

async function showUserProfile(userId) {
  try {
    const response = await fetch(`/user/${userId}/profile`, {
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    });

    if (response.ok) {
      const user = await response.json();

      // 사용자 프로필 모달 표시
      const modalHtml = `
          <div id="userProfileModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
              <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold">사용자 프로필</h3>
                <button onclick="closeUserProfileModal()" class="text-gray-500 hover:text-gray-700">
                  <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                </button>
              </div>
              
              <div class="space-y-3">
                <div>
                  <label class="text-sm font-medium text-gray-600">이름</label>
                  <p class="text-sm text-gray-900">${
                    user.name || "정보 없음"
                  }</p>
                </div>
                
                <div>
                  <label class="text-sm font-medium text-gray-600">이메일</label>
                  <p class="text-sm text-gray-900">${
                    user.email || "정보 없음"
                  }</p>
                </div>
                
                <div>
                  <label class="text-sm font-medium text-gray-600">관심 분야</label>
                  <p class="text-sm text-gray-900">
                    ${
                      user.interest_of_subject &&
                      user.interest_of_subject.length > 0
                        ? user.interest_of_subject.join(", ")
                        : "정보 없음"
                    }
                  </p>
                </div>
                
                <div>
                  <label class="text-sm font-medium text-gray-600">소개</label>
                  <p class="text-sm text-gray-900">${
                    user.description || "정보 없음"
                  }</p>
                </div>
              </div>
            </div>
          </div>
        `;

      document.body.insertAdjacentHTML("beforeend", modalHtml);
    } else {
      alert("사용자 정보를 불러올 수 없습니다.");
    }
  } catch (error) {
    console.error("사용자 프로필 조회 오류:", error);
    alert("프로필 조회 중 오류가 발생했습니다.");
  }
}

function closeUserProfileModal() {
  const modal = document.getElementById("userProfileModal");
  if (modal) {
    modal.remove();
  }
}
