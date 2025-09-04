async function withdrawApplication(studyId) {
  if (!confirm("정말로 지원을 철회하시겠습니까?")) {
    return;
  }

  try {
    const response = await fetch(`/study/${studyId}/withdraw`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
    });

    if (response.ok) {
      alert("지원이 철회되었습니다.");
      // 페이지 새로고침 또는 상세보기 닫기
      closeDetail();
    } else {
      const errorText = await response.text();
      alert(`철회 실패: ${errorText}`);
    }
  } catch (error) {
    console.error("지원 철회 오류:", error);
    alert("철회 처리 중 오류가 발생했습니다. 다시 시도해주세요.");
  }
}

async function applyToStudy(studyId) {
  const selectedDates = [];
  const checkboxes = document.querySelectorAll(
    ' input[name="selected_dates" ]:checked'
  );
  checkboxes.forEach((checkbox) => {
    selectedDates.push(checkbox.value);
  });
  if (selectedDates.length === 0) {
    alert("참여하고 싶은 날짜를 선택해주세요.");
    return;
  }
  try {
    const response = await fetch(`/study/${studyId}/apply`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ selected_dates: selectedDates }),
    });
    if (response.ok) {
      alert("스터디 참여 신청이 완료되었습니다!");
      closeDetail();
    } else {
      const errorText = await response.text();
      alert(`신청 실패: ${errorText}`);
    }
  } catch (error) {
    console.error("스터디 신청 오류:", error);
    alert("신청 중 오류가 발생했습니다. 다시 시도해주세요.");
  }
}
